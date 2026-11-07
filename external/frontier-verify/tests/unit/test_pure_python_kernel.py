from frontier_verify.recomputation.pure_python_kernel import DeterministicKernel, claimed_output_digest


def test_same_input_same_digest():
    data = {"vector": [0.1] * 8}
    assert claimed_output_digest(data) == claimed_output_digest(data)


def test_kernel_rejects_wrong_dimension():
    try:
        DeterministicKernel().forward([0.0] * 7)
        assert False
    except ValueError:
        pass


def test_small_input_change_changes_output_digest():
    a = {"vector": [0.0] * 8}
    b = {"vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]}
    assert claimed_output_digest(a) != claimed_output_digest(b)
