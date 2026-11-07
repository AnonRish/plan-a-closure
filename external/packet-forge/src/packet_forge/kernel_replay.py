"""Ground truth from a live Linux TCP stack.

A TUN device is created; the kernel owns 10.99.0.1 on it and listens on a TCP port.  This process plays
the remote host 10.99.0.2: it performs the handshake with hand-built packets, injects a case's segments
in the case's arrival order, and then reads from the accepted socket exactly what an application would
receive.  Requires root (CAP_NET_ADMIN) and /dev/net/tun.
"""
from __future__ import annotations

import fcntl
import os
import platform
import select
import socket
import struct
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from . import frames as fr
from .corpus import Ack, Case, Seg, expected_for_case, server_isn
from .parse import parse_frame
from .pcap import LINKTYPE_RAW

TUNSETIFF = 0x400454CA
IFF_TUN, IFF_NO_PI = 0x0001, 0x1000
KERNEL_IP, PEER_IP = "10.99.0.1", "10.99.0.2"


class KernelUnavailable(RuntimeError):
    pass


@dataclass
class Observation:
    data: bytes
    eof: bool
    reset: bool
    handshake_ok: bool = True


def kernel_available() -> Optional[str]:
    """None when the harness can run, otherwise the reason it cannot."""
    if platform.system() != "Linux":
        return "not Linux"
    if not os.path.exists("/dev/net/tun"):
        return "/dev/net/tun missing"
    if os.geteuid() != 0:
        return "needs root"
    try:
        fd = os.open("/dev/net/tun", os.O_RDWR)
        os.close(fd)
    except OSError as e:
        return "cannot open /dev/net/tun: %s" % e
    for tool in ("ip",):
        if subprocess.call(["which", tool], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
            return "`%s` not installed" % tool
    return None


class KernelBench:
    def __init__(self, ifname: str = "pfkern0", port: int = 5001):
        why = kernel_available()
        if why:
            raise KernelUnavailable(why)
        self.ifname, self.port = ifname, port
        self.fd = os.open("/dev/net/tun", os.O_RDWR)
        fcntl.ioctl(self.fd, TUNSETIFF, struct.pack("16sH22x", ifname.encode(), IFF_TUN | IFF_NO_PI))
        os.set_blocking(self.fd, False)
        subprocess.check_call(["ip", "addr", "add", KERNEL_IP + "/24", "dev", ifname])
        subprocess.check_call(["ip", "link", "set", ifname, "up"])
        for path, val in (("/proc/sys/net/ipv6/conf/%s/disable_ipv6" % ifname, "1"),
                          ("/proc/sys/net/ipv4/conf/%s/rp_filter" % ifname, "0")):
            try:
                with open(path, "w") as f:
                    f.write(val)
            except OSError:
                pass
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((KERNEL_IP, port))
        self.listener.listen(256)
        self._next_port = 20000
        self.kernel = platform.release()

    def close(self) -> None:
        try:
            self.listener.close()
        finally:
            os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # -- plumbing -----------------------------------------------------------------------------------
    def _drain(self) -> List[bytes]:
        out = []
        while True:
            try:
                out.append(os.read(self.fd, 65535))
            except BlockingIOError:
                return out

    def _send(self, cport: int, seq: int, ack: int, flags: int, payload: bytes = b"", options: bytes = b"",
              bad_tcp: bool = False, frag: bool = False) -> None:
        pkt = fr.tcp_ip_packet(PEER_IP, KERNEL_IP, cport, self.port, seq, ack, flags, payload, options=options,
                               ident=self._next_port & 0xFFFF, bad_tcp_checksum=bad_tcp)
        if frag:
            for f in fr.fragment_ipv4(pkt, 24):
                os.write(self.fd, f)
        else:
            os.write(self.fd, pkt)

    def _wait_synack(self, cport: int, timeout: float = 2.0) -> Optional[int]:
        end = time.time() + timeout
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if not r:
                continue
            for raw in self._drain():
                seg, _ = parse_frame(0, 0, raw, LINKTYPE_RAW)
                if seg and seg.sport == self.port and seg.dport == cport and seg.syn and seg.has_ack:
                    return seg.seq
        return None

    # -- one conversation ---------------------------------------------------------------------------
    def run_case(self, case: Case, settle: float = 0.03) -> Observation:
        if not case.handshake:
            raise ValueError("case has no handshake; nothing to replay against a listening socket")
        cport = self._next_port
        self._next_port += 1
        isn = case.isn & 0xFFFFFFFF
        base = (isn + 1) & 0xFFFFFFFF
        syn_ev = next((e for e in case.events if isinstance(e, Seg) and e.syn), None)
        self._send(cport, isn, 0, fr.SYN, syn_ev.data if syn_ev else b"", options=bytes([2, 4, 0x05, 0xB4]))
        sisn = self._wait_synack(cport)
        if sisn is None:
            return Observation(b"", False, False, handshake_ok=False)
        sack = (sisn + 1) & 0xFFFFFFFF
        self._send(cport, base, sack, fr.ACK)
        self.listener.settimeout(2.0)
        conn, _ = self.listener.accept()
        try:
            for ev in case.events:
                if isinstance(ev, Ack) or ev.syn:
                    continue
                flags = fr.ACK | (fr.PSH if ev.data else 0) | (fr.FIN if ev.fin else 0)
                self._send(cport, (base + ev.off) & 0xFFFFFFFF, sack, flags, ev.data, bad_tcp=ev.bad_csum,
                           frag=ev.frag)
                self._drain()
            time.sleep(settle)
            self._drain()
            data, eof, reset = bytearray(), False, False
            conn.setblocking(False)
            while True:
                r, _, _ = select.select([conn], [], [], settle)
                if not r:
                    break
                try:
                    chunk = conn.recv(65536)
                except ConnectionResetError:
                    reset = True
                    break
                except BlockingIOError:
                    break
                if not chunk:
                    eof = True
                    break
                data += chunk
            return Observation(bytes(data), eof, reset)
        finally:
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            conn.close()
            self._drain()


# Documented places where the `linux` policy is known not to reproduce the kernel (see docs/VERIFICATION.md).
KNOWN_DEVIATIONS = {
    "ov-chain-three-ooo": "Consistent with the kernel's out-of-order queue appending a segment to a buffered one that ends "
                          "where it starts, so that segment (C) inherits the earlier one's start offset and beats B; "
                          "the model ranks C by its own start.  The mechanism is inferred from the kernel's output, "
                          "not read from kernel source (see VERIFICATION_LOG.md, K1).",
}


def fuzz_scenario(rng, i: int) -> Case:
    """A random 2-5 segment overlap scenario whose missing prefix is supplied at a random position."""
    from .corpus import STREAM
    n = rng.randint(2, 5)
    segs = []
    letters = "ABCDEFG"
    for k in range(n):
        segs.append(Seg(rng.randint(4, 30), (letters[k] * rng.randint(1, 12)).encode()))
    lo = min(sg.off for sg in segs)
    order = segs[:]
    if lo > 0:
        order.insert(rng.choice([0, len(order), rng.randint(0, len(order))]), Seg(0, STREAM[:lo]))
    return Case("fuzz%d" % i, "random overlap scenario", "overlap", "", 0x50000000 + i, tuple(order))


def kernel_fuzz(n: int, seed: int, bench: Optional["KernelBench"] = None) -> dict:
    """Replay ``n`` random scenarios; count how often each policy reproduces the kernel's bytes."""
    import random
    rng = random.Random(seed)
    own = bench is None
    bench = bench or KernelBench()
    try:
        counts: Dict[str, int] = {}
        misses = []
        for i in range(n):
            c = fuzz_scenario(rng, i)
            obs = bench.run_case(c)
            exp = expected_for_case(c)
            for name, st in exp["streams"].items():
                counts[name] = counts.get(name, 0) + (bytes.fromhex(st["hex"]) == obs.data)
            if bytes.fromhex(exp["streams"]["linux"]["hex"]) != obs.data:
                misses.append({"events": [(e.off, e.off + len(e.data), e.data[:1].decode()) for e in c.events],
                               "kernel": obs.data.decode("latin1"),
                               "model": bytes.fromhex(exp["streams"]["linux"]["hex"]).decode("latin1")})
        return {"scenarios": n, "seed": seed, "kernel": bench.kernel, "agree": counts, "linux_misses": misses}
    finally:
        if own:
            bench.close()


def kernel_verify(cases: Sequence[Case], bench: Optional[KernelBench] = None) -> Dict[str, dict]:
    """Replay ``cases`` and compare the bytes the kernel delivers with every policy's prediction."""
    own = bench is None
    bench = bench or KernelBench()
    try:
        results: Dict[str, dict] = {}
        for c in cases:
            if not c.handshake:
                continue
            obs = bench.run_case(c)
            exp = expected_for_case(c, endpoint_view=True)
            matches = [name for name, s in exp["streams"].items() if bytes.fromhex(s["hex"]) == obs.data]
            results[c.id] = {
                "observed_hex": obs.data.hex(), "eof": obs.eof, "reset": obs.reset,
                "handshake_ok": obs.handshake_ok,
                "matches_policies": matches,
                "linux_model_matches": "linux" in matches,
                "expected_linux_hex": exp["streams"]["linux"]["hex"],
            }
        return results
    finally:
        if own:
            bench.close()
