import hashlib
import math
import random
import struct

import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from weight_diode import Encoder, LossyLink, Receiver
from weight_diode import receiver as R
from weight_diode.format import HDR, SYM

KEY = Ed25519PrivateKey.generate()
DATA = np.random.default_rng(0).integers(0, 256, 30_000, dtype=np.uint8).tobytes()


def make_enc(data=DATA, S=128, k=10, r=6, serial=1, label="t", key=KEY, **kw):
    return Encoder(data, key, symbol_size=S, k=k, r=r, serial=serial, label=label, **kw)


ENC = make_enc()          # 24 blocks of 16 coded symbols


def run(enc, packets, **rx_kw):
    rx = Receiver(rx_kw.pop("keys", [KEY.public_key()]), **rx_kw)
    for p in packets:
        rx.feed(p)
    return rx


def ok(rx, enc=ENC, data=DATA):
    return rx.result(enc.manifest_id) == data


# ------------------------------------------------------------------ transfer under impairment
def test_clean_transfer_and_progress_api():
    rx = run(ENC, ENC.stream(passes=1))
    assert ok(rx) and rx.completed_ids() == [ENC.manifest_id]
    assert rx.progress(ENC.manifest_id) == (24, 24)
    assert rx.stats[R.COMPLETE] == 1 and rx.stats[R.SYMBOL_BAD_PROOF] == 0


@pytest.mark.parametrize("loss,passes", [(0.1, 1), (0.3, 3), (0.5, 6)])
def test_random_loss_including_manifest_datagrams(loss, passes):
    for seed in range(5):
        rx = run(ENC, LossyLink(loss, seed=seed).transmit(ENC.stream(passes=passes)))
        assert ok(rx), (loss, passes, seed)


def test_contiguous_burst_kills_sequential_order_but_not_interleaved_order():
    burst = (60, 20)                                             # 20 consecutive packets in the middle of the pass
    good = run(ENC, LossyLink(drop_range=burst).transmit(ENC.stream(passes=1, interleave=True)))
    bad = run(ENC, LossyLink(drop_range=burst).transmit(ENC.stream(passes=1, interleave=False)))
    assert ok(good)                                              # each of 24 blocks loses at most 1 symbol (r = 6)
    assert not ok(bad)                                           # some block loses at least 7 symbols in one pass
    assert bad.progress(ENC.manifest_id)[0] < 24


def test_interleaving_bound_holds_for_every_window_length():
    B = ENC.n_blocks
    blocks = [struct.unpack_from(">I", p, HDR.size)[0] for p in ENC.one_pass(interleave=True)]
    for L in (1, 5, 24, 25, 50, 96):
        worst = max(max(np.bincount(blocks[i:i + L], minlength=B)) for i in range(0, len(blocks) - L + 1))
        assert worst <= math.ceil(L / B), L


def test_reordering_and_duplication():
    rx = run(ENC, LossyLink(reorder_window=40, dup=0.3, seed=2).transmit(ENC.stream(passes=1)))
    assert ok(rx) and rx.stats[R.SYMBOL_DUPLICATE] > 0


def test_late_join_drops_only_the_symbols_before_the_next_manifest_then_completes():
    pkts = list(ENC.stream(passes=2))
    start = next(i for i in range(int(len(pkts) * 0.45), len(pkts)) if pkts[i] != ENC.manifest_packet
                 and pkts[i - 1] == ENC.manifest_packet) + 1          # join just after a manifest, one symbol into the gap
    rx = run(ENC, pkts[start:])
    assert ok(rx)
    dropped = rx.stats[R.SYMBOL_NO_SESSION]
    assert 0 < dropped <= 32                                          # those before the next periodic manifest, no more


def test_gilbert_elliott_bursty_channel_with_a_few_passes():
    rx = run(ENC, LossyLink(ge=(0.02, 0.2, 0.0, 0.9), seed=5).transmit(ENC.stream(passes=4)))
    assert ok(rx)


def test_two_files_on_one_link_are_routed_by_manifest_id():
    other = make_enc(data=DATA[::-1], label="other")
    mixed = [p for pair in zip(ENC.stream(passes=1), other.stream(passes=1)) for p in pair]
    rx = run(ENC, mixed)
    assert ok(rx) and rx.result(other.manifest_id) == DATA[::-1] and len(rx.completed_ids()) == 2


@pytest.mark.parametrize("size", [0, 1, 1279, 1280, 1281, 5000])
def test_boundary_file_sizes(size):
    d = bytes(range(256)) * 30
    enc = make_enc(data=d[:size])
    assert ok(run(enc, enc.stream(passes=1)), enc, d[:size])


# ------------------------------------------------------------------ security
def test_bit_flips_are_never_accepted_and_the_file_still_arrives():
    rx = run(ENC, LossyLink(corrupt=0.08, seed=9).transmit(ENC.stream(passes=4)))
    assert ok(rx)
    rejected = rx.stats[R.SYMBOL_BAD_PROOF] + rx.stats[R.MALFORMED] + rx.stats[R.SYMBOL_MALFORMED] + rx.stats[R.SYMBOL_NO_SESSION]
    assert rejected + rx.stats[R.MANIFEST_INVALID] + rx.stats[R.MANIFEST_SIGNATURE] > 0


def test_forged_symbols_with_random_payload_and_proof_are_rejected():
    rx = run(ENC, [ENC.manifest_packet])
    rng = random.Random(1)
    from weight_diode.merkle import proof_length
    n_forged = 0
    for b in range(ENC.n_blocks):
        for j in range(ENC.n):
            plen = proof_length(b * ENC.n + j, ENC.n_blocks * ENC.n)
            pkt = (HDR.pack(b"WDIO", 1, 1, 0, 0, ENC.manifest_id) + SYM.pack(b, j) + rng.randbytes(ENC.S) + rng.randbytes(32 * plen))
            assert rx.feed(pkt) == R.SYMBOL_BAD_PROOF
            n_forged += 1
    assert rx.progress(ENC.manifest_id) == (0, 24) and n_forged == 24 * 16
    for p in ENC.stream(passes=1):                                             # the genuine stream still completes afterwards
        rx.feed(p)
    assert ok(rx)


def test_attacker_symbols_from_their_own_valid_tree_do_not_verify_against_the_signed_root():
    evil = make_enc(data=b"E" * len(DATA), key=Ed25519PrivateKey.generate())   # a perfectly valid tree, different root
    rx = run(ENC, [ENC.manifest_packet])
    forged = []
    for b in range(ENC.n_blocks):
        for j in range(ENC.n):
            pkt = bytearray(evil.symbol_packet(b, j))
            pkt[8:16] = ENC.manifest_id                                        # address it to the genuine session
            forged.append(bytes(pkt))
    assert {rx.feed(p) for p in forged} == {R.SYMBOL_BAD_PROOF}
    assert rx.progress(ENC.manifest_id)[0] == 0


def test_position_replay_and_cross_manifest_replay_are_rejected():
    rx = run(ENC, [ENC.manifest_packet])
    from weight_diode.merkle import proof_length
    N = ENC.n_blocks * ENC.n
    pkt = bytearray(ENC.symbol_packet(0, 3))
    for j2 in range(ENC.n):
        if j2 != 3 and proof_length(j2, N) == proof_length(3, N):
            moved = bytearray(pkt)
            moved[HDR.size + 4:HDR.size + 6] = struct.pack(">H", j2)           # same payload claimed at another position
            assert rx.feed(bytes(moved)) == R.SYMBOL_BAD_PROOF
            break
    else:
        pytest.fail("no same-length position found")
    other = make_enc(data=DATA[::-1], label="other")
    rx2 = run(ENC, [ENC.manifest_packet, other.manifest_packet])
    replay = bytearray(other.symbol_packet(0, 0))
    replay[8:16] = ENC.manifest_id
    assert rx2.feed(bytes(replay)) in (R.SYMBOL_BAD_PROOF, R.SYMBOL_MALFORMED)
    assert rx2.progress(ENC.manifest_id)[0] == 0


def test_untrusted_signer_is_rejected_and_its_symbols_find_no_session():
    stranger = make_enc(key=Ed25519PrivateKey.generate())
    rx = run(ENC, [stranger.manifest_packet])
    assert rx.stats[R.MANIFEST_SIGNATURE] == 1
    assert rx.feed(stranger.symbol_packet(0, 0)) == R.SYMBOL_NO_SESSION


def test_whitelist_admits_only_approved_file_hashes():
    approved = hashlib.sha256(DATA).hexdigest()
    ok_rx = run(ENC, ENC.stream(passes=1), whitelist=[approved])
    assert ok(ok_rx)
    bad = make_enc(data=DATA[::-1], label="unapproved")                        # validly signed, but not on the list
    rx = run(bad, bad.stream(passes=1), whitelist=[approved])
    assert rx.stats[R.MANIFEST_WHITELIST] >= 1 and rx.result(bad.manifest_id) is None and not rx.sessions
    assert rx.feed(bad.symbol_packet(0, 0)) == R.SYMBOL_NO_SESSION


def test_rollback_protection_by_serial():
    old = make_enc(serial=3)
    rx = run(old, old.stream(passes=1), min_serial=5)
    assert rx.stats[R.MANIFEST_SERIAL] >= 1 and not rx.sessions
    new = make_enc(serial=5)
    assert ok(run(new, new.stream(passes=1), min_serial=5), new)


def test_a_signer_that_lies_about_the_file_hash_releases_nothing():
    liar = make_enc(_lie_about_hash=True)
    rx = run(liar, liar.stream(passes=1))
    assert rx.stats[R.FILE_HASH_MISMATCH] == 1
    assert rx.result(liar.manifest_id) is None and rx.completed_ids() == []
    assert rx.stats[R.SYMBOL_BAD_PROOF] == 0                                   # every symbol verified; the manifest lied


def test_resource_limits():
    rx = run(ENC, [ENC.manifest_packet], max_file_size=1000)
    assert rx.stats[R.MANIFEST_LIMITS] == 1 and not rx.sessions
    rx = run(ENC, [ENC.manifest_packet], max_tree_size=100)
    assert rx.stats[R.MANIFEST_LIMITS] == 1
    rx = Receiver([KEY.public_key()], max_sessions=1)
    a, b = make_enc(label="a"), make_enc(data=DATA[::-1], label="b")
    assert rx.feed(a.manifest_packet) == R.MANIFEST_ACCEPTED
    assert rx.feed(b.manifest_packet) == R.MANIFEST_LIMITS and len(rx.sessions) == 1


def test_manifest_with_a_mismatched_header_id_is_invalid_and_not_cached():
    pkt = bytearray(ENC.manifest_packet)
    pkt[8:16] = bytes(8)
    rx = Receiver([KEY.public_key()])
    assert rx.feed(bytes(pkt)) == R.MANIFEST_INVALID
    assert rx.feed(ENC.manifest_packet) == R.MANIFEST_ACCEPTED                 # the real one is unaffected
    assert rx.feed(ENC.manifest_packet) == R.MANIFEST_DUPLICATE


def test_fuzz_never_raises_and_never_lets_a_wrong_byte_through():
    rng = random.Random(7)
    seeds = [ENC.manifest_packet] + [ENC.symbol_packet(b, j) for b in range(0, 24, 5) for j in range(0, 16, 3)]
    rx = Receiver([KEY.public_key()])
    rx.feed(ENC.manifest_packet)
    for _ in range(6000):
        r = rng.random()
        if r < 0.25:
            pkt = rng.randbytes(rng.randint(0, 400))
        else:
            b = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 4)):
                if b:
                    b[rng.randrange(len(b))] = rng.randrange(256)
            if rng.random() < 0.2:
                b = b[:rng.randint(0, len(b))]
            if rng.random() < 0.1:
                b += rng.randbytes(rng.randint(1, 40))
            pkt = bytes(b)
        rx.feed(pkt)                                                            # must not raise
    for p in ENC.stream(passes=1):
        rx.feed(p)
    assert ok(rx)                                                               # nothing the fuzzer sent corrupted the result


def test_receiver_has_no_transmit_surface():
    public = [n for n in dir(Receiver) if not n.startswith("_")]
    assert sorted(public) == ["completed_ids", "feed", "progress", "result"]
    assert isinstance(Receiver([]).feed(b""), str)                              # returns an event label, never bytes to send
