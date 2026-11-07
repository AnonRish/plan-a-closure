"""Loss tolerance and overhead, in closed form. The tests check every function against simulation or exact counting."""
from __future__ import annotations

import math

from .format import HDR, SYM
from .merkle import max_proof_length, total_proof_length


def _log_binom_pmf(n: int, j: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if j == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if j == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
            + j * math.log(p) + (n - j) * math.log1p(-p))


def block_success_probability(k: int, r: int, loss: float, passes: int = 1) -> float:
    """P(a block decodes) = P(at least k of n = k + r symbols arrive), independent loss ``loss`` per transmission.

    With ``passes`` carousel passes a symbol is missing only if every one of its transmissions is lost.
    """
    if not (0.0 <= loss <= 1.0) or k < 1 or r < 0 or passes < 1:
        raise ValueError("bad arguments")
    n, q = k + r, 1.0 - loss ** passes
    return min(1.0, math.fsum(math.exp(_log_binom_pmf(n, j, q)) for j in range(k, n + 1)))


def file_success_probability(n_blocks: int, k: int, r: int, loss: float, passes: int = 1) -> float:
    return block_success_probability(k, r, loss, passes) ** n_blocks


def min_redundancy(k: int, n_blocks: int, loss: float, target_failure: float, passes: int = 1) -> int:
    """Smallest ``r`` (with ``k + r <= 256``) so the whole file fails with probability at most ``target_failure``."""
    for r in range(0, 256 - k + 1):
        if 1.0 - file_success_probability(n_blocks, k, r, loss, passes) <= target_failure:
            return r
    raise ValueError("no r <= 256 - k meets the target at this loss rate")


def wire_overhead(file_size: int, symbol_size: int, k: int, r: int) -> dict:
    """Exact bytes of one pass of symbol datagrams, broken down, against the file size."""
    from .format import Manifest
    B = Manifest.blocks_for(file_size, k, symbol_size)
    n, N = k + r, B * (k + r)
    proofs = 32 * total_proof_length(N)
    payload = N * symbol_size
    headers = N * (HDR.size + SYM.size)
    total = payload + proofs + headers
    padding = B * k * symbol_size - file_size
    return {"n_blocks": B, "symbols": N, "payload_bytes": payload, "proof_bytes": proofs, "header_bytes": headers,
            "wire_bytes_per_pass": total, "padding_bytes": padding, "overhead_vs_file": total / file_size if file_size else math.inf,
            "erasure_share": r / n, "loss_tolerated_per_block": r / n}


def transfer_seconds(wire_bytes: float, link_gbps: float, passes: int = 1) -> float:
    if link_gbps <= 0:
        raise ValueError("link rate must be positive")
    return wire_bytes * passes * 8 / (link_gbps * 1e9)


IP_UDP_HEADERS = 28      # IPv4 (20) + UDP (8); IPv6 would be 48


def max_symbol_size(mtu: int, tree_size: int, ip_udp_headers: int = IP_UDP_HEADERS) -> int:
    """Largest symbol size whose *longest* datagram still fits one link frame of ``mtu`` bytes without IP fragmentation.

    Fragmented datagrams are lost if any fragment is lost, which silently multiplies the effective loss rate.
    Datagram size is ``16 (header) + 6 (block, index) + symbol_size + 32 * proof_length``.
    """
    room = mtu - ip_udp_headers - HDR.size - SYM.size - 32 * max_proof_length(tree_size)
    if room < 1:
        raise ValueError("MTU too small for this tree size: the Merkle proof alone does not fit")
    return room


def max_datagram_bytes(symbol_size: int, tree_size: int) -> int:
    return HDR.size + SYM.size + symbol_size + 32 * max_proof_length(tree_size)
