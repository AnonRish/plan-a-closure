"""Impairment models for tests and a real UDP glue. The UDP receiver only ever calls ``bind`` and ``recvfrom``."""
from __future__ import annotations

import random
import socket
import time


class LossyLink:
    """In-memory one-way channel: independent loss, Gilbert-Elliott bursts, reordering, duplication, bit flips."""

    def __init__(self, loss: float = 0.0, *, ge: tuple | None = None, reorder_window: int = 0, dup: float = 0.0,
                 corrupt: float = 0.0, seed: int = 0, drop_range: tuple | None = None):
        self.loss, self.ge, self.window, self.dup, self.corrupt = loss, ge, reorder_window, dup, corrupt
        self.drop_range = drop_range
        self.rng = random.Random(seed)
        self.sent = self.delivered = 0

    def _drop(self, i: int, bad_state: list) -> bool:
        if self.drop_range and self.drop_range[0] <= i < self.drop_range[0] + self.drop_range[1]:
            return True
        if self.ge:                                       # (p_good_to_bad, p_bad_to_good, loss_in_good, loss_in_bad)
            p_gb, p_bg, l_g, l_b = self.ge
            bad_state[0] = (self.rng.random() >= p_bg) if bad_state[0] else (self.rng.random() < p_gb)
            return self.rng.random() < (l_b if bad_state[0] else l_g)
        return self.rng.random() < self.loss

    def transmit(self, packets):
        held, bad = [], [False]
        for i, pkt in enumerate(packets):
            self.sent += 1
            if self._drop(i, bad):
                continue
            if self.corrupt and self.rng.random() < self.corrupt:
                b = bytearray(pkt)
                b[self.rng.randrange(len(b))] ^= 1 << self.rng.randrange(8)
                pkt = bytes(b)
            copies = 2 if self.dup and self.rng.random() < self.dup else 1
            for _ in range(copies):
                if self.window:
                    held.append(pkt)
                    if len(held) >= self.window:
                        self.rng.shuffle(held)
                        for h in held:
                            self.delivered += 1
                            yield h
                        held = []
                else:
                    self.delivered += 1
                    yield pkt
        self.rng.shuffle(held)
        for h in held:
            self.delivered += 1
            yield h


def udp_send(packets, addr: tuple, *, burst: int = 64, pause: float = 0.0005) -> int:
    """Send datagrams, pausing briefly every ``burst`` packets so loopback buffers are not overrun. Returns the count."""
    n = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for pkt in packets:
            s.sendto(pkt, addr)
            n += 1
            if burst and n % burst == 0 and pause:
                time.sleep(pause)
    return n


def udp_receive(receiver, host: str, port: int, *, timeout: float = 10.0, ready=None, until_complete: bool = True,
                rcvbuf: int = 8 << 20) -> None:
    """Bind, then ``recvfrom`` in a loop and hand datagrams to ``receiver``. Sends nothing, ever."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
        s.bind((host, port))
        s.settimeout(0.2)
        if ready is not None:
            ready.set()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, _peer = s.recvfrom(65535)
            except socket.timeout:
                continue
            receiver.feed(data)
            if until_complete and receiver.completed_ids():
                return
