"""
End-to-end demonstration of Fides: an honest device, a device caught
outright, and a device running a subtler covert-training attack, followed
by the detection-probability math behind why repeated sampling closes the
gap over time. Run with: python examples/demo.py
"""

from fides.trace import generate_inference_epoch, generate_training_epoch, generate_mixed_epoch
from fides.protocol import Tap
from fides.security import detection_probability, repeated_detection_probability
from fides.accumulator import trusted_setup
from fides.zk_verification import ZKProver, ZKVerifier


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main():
    section("Fides -- packet-hashing inference-only verification tap")

    section("[1] Honest device: 5 genuine inference epochs")
    honest = Tap(device_id="gpu-honest-001", sample_rate=0.15, seed=1)
    for i in range(5):
        epoch = generate_inference_epoch(epoch_id=i, seq_position=i * 100, seed=i)
        commitment, result = honest.run_epoch(epoch)
        print(f"  epoch {i}: declared={commitment.declared_class:10s} "
              f"n_events={commitment.n_events:3d}  audit_ok={result.consistent}")
    print(f"  -> ledger has {len(honest.ledger)} entries, chain valid: {honest.ledger.verify_chain()}")

    section("[2] Blatant liar: full training epochs declared 'inference'")
    liar = Tap(device_id="gpu-liar-001", sample_rate=0.15, seed=2)
    for i in range(3):
        epoch = generate_training_epoch(epoch_id=i, seed=i)
        commitment, result = liar.run_epoch(epoch, declared_override="inference")
        print(f"  epoch {i}: declared=inference  audit_ok={result.consistent}  ({result.reason})")

    section("[3] Subtle attacker: mostly-inference epochs with covert gradient steps mixed in")
    subtle = Tap(device_id="gpu-subtle-001", sample_rate=0.15, seed=3)
    caught_at = None
    for i in range(15):
        epoch = generate_mixed_epoch(epoch_id=i, sneak_layers=1, seed=i)
        commitment, result = subtle.run_epoch(epoch, declared_override="inference")
        status = "CAUGHT" if not result.consistent else "not caught this epoch"
        print(f"  epoch {i:2d}: n_events={commitment.n_events:3d}  audit_ok={result.consistent}  {status}")
        if not result.consistent and caught_at is None:
            caught_at = i
    print(f"\n  -> first caught at epoch {caught_at}" if caught_at is not None
          else "\n  -> not caught in 15 epochs this run (see probability model below)")

    section("[4] Tamper-evident ledger: a compromised auditor tries to erase a finding")
    print(f"  subtle-attacker ledger chain valid before tampering: {subtle.ledger.verify_chain()}")
    if caught_at is not None:
        subtle.ledger.tamper(caught_at, "signature + sampled proofs verified; no training signal in sample")
        print(f"  ... auditor silently rewrites epoch {caught_at}'s finding to look clean ...")
        print(f"  ledger chain valid after tampering:              {subtle.ledger.verify_chain()}")

    section("[5] Detection-probability math (spec/PROTOCOL.md section 5)")
    n, k, m = 28, 3, 5  # ~ the mixed-epoch shape: 1 sneak layer -> 3 bad events in ~28 total
    p = detection_probability(n, k, m)
    print(f"  single-epoch catch probability at n={n}, k={k} bad events, m={m} sampled: {p:.3f}")
    for epochs in (1, 2, 3, 5, 10, 20):
        print(f"    P(caught within {epochs:2d} epoch(s)): {repeated_detection_probability(p, epochs):.5f}")

    section("[6] Same question, cryptographic certainty instead of sampling (spec/PROTOCOL.md section 8)")
    print("  generating a fresh RSA accumulator setup (2048-bit modulus)...")
    setup = trusted_setup(key_size=2048)
    zk_prover, zk_verifier = ZKProver(setup), ZKVerifier(setup)

    honest_epoch = generate_inference_epoch(epoch_id=0, seed=1)
    honest_proof = zk_prover.prove_inference_only(honest_epoch)
    print(f"  honest inference epoch:  proof verifies = {zk_verifier.verify(honest_proof)}")

    caught = 0
    trials = 20
    for trial in range(trials):
        mixed = generate_mixed_epoch(epoch_id=0, sneak_layers=1, seed=trial)
        proof = zk_prover.prove_inference_only(mixed)
        if not zk_verifier.verify(proof):
            caught += 1
    print(f"  same subtle 1-sneak-layer attack, {trials} independent trials:  caught {caught}/{trials}")
    print("  (section [3]/[5] above show this same attack caught ~40-50% of the time,")
    print("   per epoch, under sampling -- here it's every time, because a forbidden")
    print("   op's non-membership witness provably cannot be constructed if it's present.)")


if __name__ == "__main__":
    main()
