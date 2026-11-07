from fides.trace import generate_training_epoch, generate_inference_epoch
from fides.features import extract


def test_training_fingerprint_has_high_backward_ratio_and_optimizer():
    epoch = generate_training_epoch(epoch_id=0, n_layers=6, seed=3)
    fp = extract(epoch)
    assert fp.backward_ratio > 0.5
    assert fp.has_optimizer_update is True
    assert fp.kv_cache_present is False


def test_inference_fingerprint_has_zero_backward_ratio_and_kv_cache():
    epoch = generate_inference_epoch(epoch_id=0, n_layers=6, seed=3)
    fp = extract(epoch)
    assert fp.backward_ratio == 0.0
    assert fp.has_optimizer_update is False
    assert fp.kv_cache_present is True


def test_fingerprint_does_not_expose_raw_event_data():
    # The fingerprint is meant to be the privacy-preserving summary: it
    # should be plain aggregate statistics, not the underlying events.
    epoch = generate_training_epoch(epoch_id=0, n_layers=2, seed=1)
    fp = extract(epoch)
    field_names = fp.__dataclass_fields__.keys()
    assert "events" not in field_names
    assert all(isinstance(getattr(fp, name), (int, float, bool)) for name in field_names)
