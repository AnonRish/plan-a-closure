from fides.trace import generate_training_epoch, generate_inference_epoch, generate_mixed_epoch
from fides.attestation import Prover, Verifier


def _run(prover, verifier, epoch, declared_override=None):
    commitment = prover.commit(epoch, declared_override=declared_override)
    sample = verifier.choose_sample(commitment.n_events)
    revealed = prover.reveal(epoch.epoch_id, sample)
    return verifier.audit(commitment, revealed)


def test_honest_inference_epochs_always_pass_audit():
    prover = Prover(device_id="gpu-honest")
    verifier = Verifier(sample_rate=0.3, rng_seed=1)
    for i in range(15):
        epoch = generate_inference_epoch(epoch_id=i, seq_position=i * 50, seed=i)
        result = _run(prover, verifier, epoch)
        assert result.consistent, result.reason


def test_blatant_training_declared_as_inference_is_caught_immediately():
    prover = Prover(device_id="gpu-blatant-liar")
    verifier = Verifier(sample_rate=0.2, rng_seed=2)
    epoch = generate_training_epoch(epoch_id=0, n_layers=8, seed=1)
    result = _run(prover, verifier, epoch, declared_override="inference")
    # a training epoch is roughly half backward/optimizer events, so even
    # a 20% sample catches it with overwhelming probability
    assert not result.consistent


def test_subtle_covert_training_caught_with_bounded_probability_per_epoch():
    trials = 300
    caught = 0
    for trial in range(trials):
        prover = Prover(device_id=f"gpu-subtle-{trial}")
        verifier = Verifier(sample_rate=0.2, rng_seed=trial)
        epoch = generate_mixed_epoch(epoch_id=0, n_layers=8, sneak_layers=1, seed=trial)
        result = _run(prover, verifier, epoch, declared_override="inference")
        if not result.consistent:
            caught += 1
    rate = caught / trials
    # a handful of bad events hidden in ~25-30 total, sampled at 20%,
    # should be caught neither ~always nor ~never in a single epoch --
    # this is the regime where the "repeated epochs" argument in
    # security.py actually matters. Wide bounds since this is empirical.
    assert 0.15 < rate < 0.85, f"empirical single-epoch catch rate {rate} outside expected band"


def test_tampered_signature_is_rejected():
    prover = Prover(device_id="gpu-tampered-sig")
    verifier = Verifier(sample_rate=0.2, rng_seed=3)
    epoch = generate_inference_epoch(epoch_id=0, seed=1)
    commitment = prover.commit(epoch)
    commitment.signature = b"\x00" * len(commitment.signature)

    sample = verifier.choose_sample(commitment.n_events)
    revealed = prover.reveal(epoch.epoch_id, sample)
    result = verifier.audit(commitment, revealed)
    assert not result.consistent
    assert "signature" in result.reason


def test_tampered_merkle_root_is_rejected():
    prover = Prover(device_id="gpu-tampered-root")
    verifier = Verifier(sample_rate=0.3, rng_seed=4)
    epoch = generate_inference_epoch(epoch_id=0, seed=1)
    commitment = prover.commit(epoch)
    commitment.root = b"\xff" * len(commitment.root)

    sample = verifier.choose_sample(commitment.n_events)
    revealed = prover.reveal(epoch.epoch_id, sample)
    result = verifier.audit(commitment, revealed)
    # signature no longer matches the (now different) signed message either
    assert not result.consistent
