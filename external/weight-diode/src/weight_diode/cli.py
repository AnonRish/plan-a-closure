"""``weight-diode``: keygen, hash, overhead, send, recv."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import analysis
from .encoder import Encoder
from .format import public_key_from_bytes
from .link import LossyLink, udp_receive, udp_send
from .receiver import Receiver


def _out(obj) -> None:
    json.dump(obj, sys.stdout, indent=2)
    sys.stdout.write("\n")


def _hostport(s: str):
    host, _, port = s.rpartition(":")
    return host or "127.0.0.1", int(port)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="weight-diode", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("keygen", help="write <out>.priv and <out>.pub (hex Ed25519 keys)")
    g.add_argument("--out", required=True)
    h = sub.add_parser("hash", help="SHA-256 of a file, for the receiver's whitelist")
    h.add_argument("--file", required=True)
    o = sub.add_parser("overhead", help="wire overhead and loss tolerance for a file size and code")
    o.add_argument("--size", type=int, required=True)
    o.add_argument("--symbol-size", type=int, default=1024)
    o.add_argument("--k", type=int, default=32)
    o.add_argument("--r", type=int, default=8)
    o.add_argument("--loss", type=float, default=0.0)
    o.add_argument("--passes", type=int, default=1)
    o.add_argument("--link-gbps", type=float, default=None)
    o.add_argument("--mtu", type=int, default=1500, help="link MTU, for the fragmentation check")
    s = sub.add_parser("send", help="send a file as a signed erasure-coded carousel over UDP")
    s.add_argument("--file", required=True)
    s.add_argument("--key", required=True, help="hex private key file from keygen")
    s.add_argument("--to", required=True, help="host:port")
    s.add_argument("--symbol-size", type=int, default=1024)
    s.add_argument("--k", type=int, default=32)
    s.add_argument("--r", type=int, default=8)
    s.add_argument("--serial", type=int, default=0)
    s.add_argument("--label", default="")
    s.add_argument("--passes", type=int, default=2)
    s.add_argument("--simulate-loss", type=float, default=0.0, help="drop this fraction of packets before sending")
    r = sub.add_parser("recv", help="receive, verify and write a file; sends nothing")
    r.add_argument("--port", type=int, required=True)
    r.add_argument("--host", default="127.0.0.1")
    r.add_argument("--pubkey", required=True, action="append", help="hex public key file (repeatable)")
    r.add_argument("--whitelist", default=None, help="file with one approved SHA-256 per line")
    r.add_argument("--min-serial", type=int, default=0)
    r.add_argument("--out", required=True)
    r.add_argument("--timeout", type=float, default=60.0)
    return p


def main(argv=None, ready: "threading.Event | None" = None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "keygen":
        key = Ed25519PrivateKey.generate()
        from cryptography.hazmat.primitives import serialization as ser
        open(a.out + ".priv", "w").write(key.private_bytes(ser.Encoding.Raw, ser.PrivateFormat.Raw, ser.NoEncryption()).hex() + "\n")
        open(a.out + ".pub", "w").write(key.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw).hex() + "\n")
        _out({"private": a.out + ".priv", "public": a.out + ".pub"})
    elif a.cmd == "hash":
        _out({"sha256": hashlib.sha256(open(a.file, "rb").read()).hexdigest()})
    elif a.cmd == "overhead":
        o = analysis.wire_overhead(a.size, a.symbol_size, a.k, a.r)
        o["block_success_probability"] = analysis.block_success_probability(a.k, a.r, a.loss, a.passes)
        o["file_success_probability"] = analysis.file_success_probability(o["n_blocks"], a.k, a.r, a.loss, a.passes)
        tree = o["symbols"]
        o["max_datagram_bytes"] = analysis.max_datagram_bytes(a.symbol_size, tree)
        o["largest_unfragmented_symbol_size"] = analysis.max_symbol_size(a.mtu, tree) if a.mtu - 28 - 22 - 32 * ((tree - 1).bit_length()) >= 1 else None
        o["fits_mtu_without_fragmentation"] = o["max_datagram_bytes"] + analysis.IP_UDP_HEADERS <= a.mtu
        if a.link_gbps:
            o["transfer_seconds"] = analysis.transfer_seconds(o["wire_bytes_per_pass"], a.link_gbps, a.passes)
        _out(o)
    elif a.cmd == "send":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as K
        key = K.from_private_bytes(bytes.fromhex(open(a.key).read().strip()))
        enc = Encoder(open(a.file, "rb").read(), key, symbol_size=a.symbol_size, k=a.k, r=a.r, serial=a.serial, label=a.label)
        pkts = enc.stream(passes=a.passes)
        if a.simulate_loss:
            pkts = LossyLink(a.simulate_loss).transmit(pkts)
        n = udp_send(pkts, _hostport(a.to))
        _out({"packets_sent": n, "manifest_id": enc.manifest_id.hex(), "file_sha256": enc.manifest.file_sha256})
    elif a.cmd == "recv":
        keys = [public_key_from_bytes(bytes.fromhex(open(p).read().strip())) for p in a.pubkey]
        wl = None if a.whitelist is None else [ln.strip() for ln in open(a.whitelist) if ln.strip()]
        rx = Receiver(keys, whitelist=wl, min_serial=a.min_serial)
        udp_receive(rx, a.host, a.port, timeout=a.timeout, ready=ready)
        done = rx.completed_ids()
        if not done:
            _out({"complete": False, "stats": dict(rx.stats)})
            return 2
        open(a.out, "wb").write(rx.result(done[0]))
        _out({"complete": True, "bytes": len(rx.result(done[0])), "stats": dict(rx.stats)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
