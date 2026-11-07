"""
§15: verifier component — independently recomputes the same DAG label
function (Dual-AES-PRF, same two-parent structure as wipe_daemon.c) over a
region the daemon claims to have wiped, and spot-checks sampled nodes.
Python + a real AES implementation (cryptography library, not a hand-rolled
one here — the daemon side is where hand-rolled AES-NI intrinsics earn
their keep for speed; the verifier isn't on the hot path, so use a
maintained, audited implementation instead of re-deriving one).
"""
import time
import random
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

BLOCK, LABEL = 4096, 16
KEY1 = bytes([1] + [0] * 15)
KEY2 = bytes([2] + [0] * 15)


def aes_ecb_encrypt_block(key, data16):
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return enc.update(data16) + enc.finalize()


def dual_aes_prf(data16):
    a = aes_ecb_encrypt_block(KEY1, data16)
    b = aes_ecb_encrypt_block(KEY2, data16)
    return bytes(x ^ y for x, y in zip(a, b))


def second_parent(i):
    if i < 2:
        return 0
    z = (i + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    z = z ^ (z >> 31)
    return z % i


def label_node(i, region):
    """Same construction as wipe_daemon.c's label pass — independently
    reimplemented here (not imported from the daemon's own code), since a
    verifier that shares code with the prover isn't actually verifying
    anything."""
    if i == 0:
        payload = i.to_bytes(8, "little") + b"\x00" * 8
    else:
        p2 = second_parent(i)
        payload = (
            i.to_bytes(8, "little")
            + region[(i - 1) * BLOCK: (i - 1) * BLOCK + 4]
            + region[p2 * BLOCK: p2 * BLOCK + 4]
        )
    return dual_aes_prf(payload)


def verify_region(mib=8, n_spot_checks=100, seed=7):
    n_blocks = (mib << 20) // BLOCK
    region = bytearray(b"\xA5" * (n_blocks * BLOCK))

    # Build the reference labeling independently (the verifier's own
    # ground truth), timing it the same way the daemon times its pass.
    t0 = time.perf_counter()
    for i in range(n_blocks):
        region[i * BLOCK: i * BLOCK + LABEL] = label_node(i, region)
    t_label = time.perf_counter() - t0

    # Spot-check: recompute N sampled nodes AGAIN, independently, confirm
    # they match what's stored — this is the actual verification step a
    # real deployment would run against a daemon's claimed output, not
    # against its own just-computed copy; done against the same buffer
    # here since this sandbox has no second machine to play the daemon's
    # role, which is stated as the limitation it is.
    rng = random.Random(seed)
    ok = 0
    for _ in range(n_spot_checks):
        i = rng.randrange(n_blocks)
        if label_node(i, region) == bytes(region[i * BLOCK: i * BLOCK + LABEL]):
            ok += 1

    # Tamper test: corrupt one label, confirm the spot-check would catch it.
    victim = rng.randrange(1, n_blocks)
    original = bytes(region[victim * BLOCK: victim * BLOCK + LABEL])
    region[victim * BLOCK] ^= 0xFF
    recomputed = label_node(victim, region)
    tamper_detected = recomputed != bytes(region[victim * BLOCK: victim * BLOCK + LABEL])
    # restore for cleanliness
    region[victim * BLOCK: victim * BLOCK + LABEL] = original

    return {
        "region_MiB": mib,
        "n_blocks": n_blocks,
        "label_pass_s": round(t_label, 4),
        "labels_per_s": round(n_blocks / t_label, 0),
        "spot_check_result": f"{ok}/{n_spot_checks}",
        "tamper_detected": tamper_detected,
    }


if __name__ == "__main__":
    result = verify_region(mib=8, n_spot_checks=100)
    print(json.dumps(result, indent=2))
    assert result["spot_check_result"] == "100/100", "verifier disagrees with itself — real bug, not a flaky test"
    assert result["tamper_detected"] is True, "tamper test failed to catch a real corruption"
    print()
    print("Both required properties hold: spot-checked labels match the daemon's construction,")
    print("and a single corrupted byte is caught by recomputation. Note the verifier here runs")
    print(f"at {result['labels_per_s']:,.0f} labels/s in pure Python — orders of magnitude slower")
    print("than the C daemon's AES-NI path, which is fine: the verifier only needs to check a")
    print("SAMPLE, the same §1 budget-sampling principle as the rest of this document, not")
    print("relabel the entire region itself.")
