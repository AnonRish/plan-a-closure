import pytest

from fides.trace import generate_inference_epoch, generate_training_epoch, generate_mixed_epoch
from fides.accumulator import trusted_setup
from fides.zk_verification import ZKProver, ZKVerifier


@pytest.fixture(scope="module")
def setup():
    return trusted_setup(key_size=1024)  # test-speed size; see accumulator.py


def test_honest_inference_epoch_proof_verifies(setup):
    prover = ZKProver(setup)
    verifier = ZKVerifier(setup)
    for i in range(5):
        epoch = generate_inference_epoch(epoch_id=i, seq_position=i * 40, seed=i)
        proof = prover.prove_inference_only(epoch)
        assert verifier.verify(proof), f"epoch {i} should have verified"


def test_training_epoch_cannot_produce_a_valid_inference_only_proof(setup):
    prover = ZKProver(setup)
    verifier = ZKVerifier(setup)
    epoch = generate_training_epoch(epoch_id=0, n_layers=6, seed=1)
    proof = prover.prove_inference_only(epoch)
    # the proof object exists (the prover always runs), but at least one
    # forbidden-op witness will be None, and verification must fail --
    # deterministically, not "usually"
    assert not verifier.verify(proof)
    assert any(w is None for w in proof.witnesses.values())


def test_mixed_epoch_with_even_one_covert_op_cannot_verify(setup):
    # This is the case Fides' sampling scheme only catches probabilistically
    # (see test_attestation.py's ~15-85% band). Here it's certain: a single
    # covert backward/optimizer op anywhere in the epoch makes its op-code
    # present in the accumulated set, so its non-membership witness cannot
    # exist, for every one of 50 independent epochs -- not most of them.
    prover = ZKProver(setup)
    verifier = ZKVerifier(setup)
    for trial in range(50):
        epoch = generate_mixed_epoch(epoch_id=0, n_layers=6, sneak_layers=1, seed=trial)
        proof = prover.prove_inference_only(epoch)
        assert not verifier.verify(proof), f"trial {trial} should never verify"


def test_forged_proof_by_omitting_the_failing_witness_still_fails(setup):
    # A dishonest prover might try to just not report a witness for the op
    # it can't prove, hoping the verifier only checks what's present.
    # ZKVerifier.verify must treat a missing witness as a failure too.
    prover = ZKProver(setup)
    verifier = ZKVerifier(setup)
    epoch = generate_training_epoch(epoch_id=0, n_layers=4, seed=2)
    proof = prover.prove_inference_only(epoch)
    for op, witness in list(proof.witnesses.items()):
        if witness is None:
            del proof.witnesses[op]
    assert not verifier.verify(proof)


def test_proof_from_a_different_setup_does_not_verify():
    # Sanity check that the proof is bound to the specific (N, g) it was
    # generated under, not just "some" valid-looking accumulator math.
    setup_a = trusted_setup(key_size=1024)
    setup_b = trusted_setup(key_size=1024)
    prover = ZKProver(setup_a)
    epoch = generate_inference_epoch(epoch_id=0, seed=1)
    proof = prover.prove_inference_only(epoch)
    verifier_wrong_setup = ZKVerifier(setup_b)
    assert not verifier_wrong_setup.verify(proof)
