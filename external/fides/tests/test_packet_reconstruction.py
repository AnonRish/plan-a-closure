import random

from fides.packet_reconstruction import commit_message, chunk_message, reconstruct_and_verify


_MESSAGE = b"the quick brown fox jumps over the lazy dog, repeatedly, for test padding " * 5


def test_message_reconstructs_correctly_regardless_of_arrival_order():
    commitment = commit_message(_MESSAGE, chunk_size=16)
    chunks = chunk_message(_MESSAGE, 16)
    indices = list(range(len(chunks)))
    random.Random(1).shuffle(indices)
    received = {i: chunks[i] for i in indices}  # scrambled insertion order
    assert reconstruct_and_verify(commitment, received, chunk_size=16)


def test_missing_packet_is_detected():
    commitment = commit_message(_MESSAGE, chunk_size=16)
    chunks = chunk_message(_MESSAGE, 16)
    received = {i: c for i, c in enumerate(chunks) if i != 2}
    assert not reconstruct_and_verify(commitment, received, chunk_size=16)


def test_tampered_packet_content_is_detected():
    commitment = commit_message(_MESSAGE, chunk_size=16)
    chunks = chunk_message(_MESSAGE, 16)
    received = dict(enumerate(chunks))
    received[3] = b"TAMPERED-CONTEN!"
    assert not reconstruct_and_verify(commitment, received, chunk_size=16)


def test_packet_misassigned_to_wrong_index_is_detected():
    commitment = commit_message(_MESSAGE, chunk_size=16)
    chunks = chunk_message(_MESSAGE, 16)
    received = dict(enumerate(chunks))
    received[0], received[1] = received[1], received[0]
    assert not reconstruct_and_verify(commitment, received, chunk_size=16)


def test_extra_unexpected_packet_is_detected():
    commitment = commit_message(_MESSAGE, chunk_size=16)
    chunks = chunk_message(_MESSAGE, 16)
    received = dict(enumerate(chunks))
    received[len(chunks)] = b"EXTRA-INJECTED-P"  # index beyond n_chunks
    assert not reconstruct_and_verify(commitment, received, chunk_size=16)


def test_different_chunk_sizes_still_commit_and_verify_correctly():
    for chunk_size in (8, 32, 64, 200):
        commitment = commit_message(_MESSAGE, chunk_size=chunk_size)
        chunks = chunk_message(_MESSAGE, chunk_size)
        received = dict(enumerate(chunks))
        assert reconstruct_and_verify(commitment, received, chunk_size=chunk_size)
