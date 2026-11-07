from fides.trace import generate_training_epoch, generate_inference_epoch
from fides.features import extract
from fides.classifier import classify, WorkloadClass


def test_classifies_training_epoch_correctly():
    epoch = generate_training_epoch(epoch_id=0, n_layers=8, seed=7)
    assert classify(extract(epoch)) == WorkloadClass.TRAINING


def test_classifies_inference_epoch_correctly():
    epoch = generate_inference_epoch(epoch_id=0, n_layers=8, seed=7)
    assert classify(extract(epoch)) == WorkloadClass.INFERENCE


def test_classification_stable_across_layer_counts():
    for n_layers in (1, 4, 8, 16, 32):
        t = generate_training_epoch(epoch_id=0, n_layers=n_layers, seed=n_layers)
        i = generate_inference_epoch(epoch_id=0, n_layers=n_layers, seed=n_layers)
        assert classify(extract(t)) == WorkloadClass.TRAINING
        assert classify(extract(i)) == WorkloadClass.INFERENCE
