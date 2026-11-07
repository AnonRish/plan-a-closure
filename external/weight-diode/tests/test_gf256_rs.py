import itertools

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from weight_diode import gf256 as gf
from weight_diode.rs import CauchyRS

RNG = np.random.default_rng


def slow_mul(a: int, b: int) -> int:
    """Shift-and-xor multiplication with reduction by 0x11D: shares nothing with the log/exp tables."""
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        if a & 0x100:
            a ^= 0x11D
        b >>= 1
    return r


def gf_matmul(A, X):
    A, X = np.asarray(A, np.uint8), np.asarray(X, np.uint8)
    out = np.zeros((A.shape[0], X.shape[1]), np.uint8)
    for j in range(A.shape[1]):
        out ^= gf.MUL[A[:, j][:, None], X[j][None, :]]
    return out


# ------------------------------------------------------------------ field
def test_multiplication_table_matches_the_independent_slow_algorithm_on_all_65536_pairs():
    a, b = np.meshgrid(np.arange(256), np.arange(256), indexing="ij")
    slow = np.array([[slow_mul(int(i), int(j)) for j in range(256)] for i in range(256)], dtype=np.uint8)
    assert np.array_equal(gf.MUL, slow)


def test_known_values_and_generator_order():
    assert gf.mul(2, 128) == 0x1D                       # x * x^7 = x^8 = x^4 + x^3 + x^2 + 1
    p, order = 1, 0
    while True:
        p = gf.mul(p, 2)
        order += 1
        if p == 1:
            break
    assert order == 255                                   # 2 generates the multiplicative group


def test_field_axioms_exhaustively():
    a = np.arange(256, dtype=np.uint8)
    M = gf.MUL
    assert np.array_equal(M, M.T)                                                     # commutative
    assert np.array_equal(M[M[a[:, None, None], a[None, :, None]], a[None, None, :]],
                          M[a[:, None, None], M[a[None, :, None], a[None, None, :]]])  # associative, all 16.7 M triples
    assert np.array_equal(M[a[:, None, None], a[None, :, None] ^ a[None, None, :]],
                          M[a[:, None, None], a[None, :, None]] ^ M[a[:, None, None], a[None, None, :]])  # distributive
    assert np.all(M[1] == a) and np.all(M[0] == 0)


def test_inverses():
    for x in range(1, 256):
        assert gf.mul(x, gf.inv(x)) == 1
    with pytest.raises(ZeroDivisionError):
        gf.inv(0)


@settings(max_examples=60, deadline=None)
@given(m=st.integers(1, 10), S=st.integers(1, 9), seed=st.integers(0, 10**6))
def test_solve_returns_a_true_solution_for_random_invertible_systems(m, S, seed):
    rng = RNG(seed)
    while True:
        A = rng.integers(0, 256, (m, m), dtype=np.uint8)
        try:
            gf.solve(A, np.zeros((m, 1), np.uint8))
            break
        except ValueError:
            continue
    X = rng.integers(0, 256, (m, S), dtype=np.uint8)
    assert np.array_equal(gf.solve(A, gf_matmul(A, X)), X)


def test_solve_rejects_singular_and_misshaped_input():
    with pytest.raises(ValueError):
        gf.solve(np.array([[1, 2], [1, 2]], np.uint8), np.zeros((2, 1), np.uint8))
    with pytest.raises(ValueError):
        gf.solve(np.eye(3, dtype=np.uint8), np.zeros((2, 1), np.uint8))


# ------------------------------------------------------------------ Reed-Solomon
@pytest.mark.parametrize("k,r", [(1, 3), (2, 2), (3, 3), (4, 3), (5, 4), (6, 6)])
def test_mds_property_exhaustively_every_k_subset_decodes(k, r):
    rs = CauchyRS(k, r)
    data = RNG(k * 100 + r).integers(0, 256, (k, 16), dtype=np.uint8)
    coded = np.vstack([data, rs.encode(data)])
    subsets = list(itertools.combinations(range(rs.n), k))
    for sub in subsets:
        assert np.array_equal(rs.decode({i: coded[i] for i in sub}), data), sub
    assert len(subsets) > 0


def test_large_code_random_and_adversarial_subsets():
    k, r = 200, 55
    rs = CauchyRS(k, r)
    rng = RNG(5)
    data = rng.integers(0, 256, (k, 8), dtype=np.uint8)
    coded = np.vstack([data, rs.encode(data)])
    n = rs.n
    subsets = {
        "no data lost": list(range(k)),
        "first r data lost, every parity used": list(range(r, k)) + list(range(k, n)),
        "last r data lost, every parity used": list(range(0, k - r)) + list(range(k, n)),
        "10 random data lost, 10 parity used": [i for i in range(k) if i not in set(rng.choice(k, 10, replace=False))]
                                                 + list(range(k, k + 10)),
    }
    for j in range(40):
        subsets[f"random {j}"] = [int(i) for i in rng.permutation(n)[:k]]
    for name, sub in subsets.items():
        sub = list(sub)
        assert len(set(sub)) == k, name
        assert np.array_equal(rs.decode({int(i): coded[int(i)] for i in sub}), data), name


def test_more_than_k_symbols_and_systematic_prefix():
    rs = CauchyRS(6, 4)
    data = RNG(1).integers(0, 256, (6, 5), dtype=np.uint8)
    coded = np.vstack([data, rs.encode(data)])
    assert np.array_equal(coded[:6], data)                                    # systematic
    assert np.array_equal(rs.decode({i: coded[i] for i in range(10)}), data)


def test_edge_parameters():
    k1 = CauchyRS(1, 4)                                                       # repetition-like code
    d = np.array([[7, 9, 200]], np.uint8)
    par = k1.encode(d)
    for i in range(4):
        assert np.array_equal(k1.decode({1 + i: par[i]}), d)
    r0 = CauchyRS(4, 0)
    dd = RNG(2).integers(0, 256, (4, 3), dtype=np.uint8)
    assert r0.encode(dd).shape == (0, 3) and np.array_equal(r0.decode({i: dd[i] for i in range(4)}), dd)
    full = CauchyRS(128, 128)                                                 # n = 256 uses every field element
    x = RNG(3).integers(0, 256, (128, 2), dtype=np.uint8)
    coded = np.vstack([x, full.encode(x)])
    assert np.array_equal(full.decode({i: coded[i] for i in range(128, 256)}), x)   # parity only
    with pytest.raises(ValueError):
        CauchyRS(200, 57)
    with pytest.raises(ValueError):
        CauchyRS(0, 3)
    assert CauchyRS(3, 2).encode(np.zeros((3, 1), np.uint8)).shape == (2, 1)


def test_linearity_of_the_code():
    rs = CauchyRS(7, 5)
    rng = RNG(4)
    a, b = rng.integers(0, 256, (2, 7, 11), dtype=np.uint8)
    assert np.array_equal(rs.encode(a ^ b), rs.encode(a) ^ rs.encode(b))
    c = 0x53
    assert np.array_equal(rs.encode(gf.MUL[c][a]), gf.MUL[c][rs.encode(a)])


def test_decode_input_validation():
    rs = CauchyRS(4, 2)
    d = np.zeros((4, 3), np.uint8)
    coded = np.vstack([d, rs.encode(d)])
    with pytest.raises(ValueError):
        rs.decode({i: coded[i] for i in range(3)})                            # too few
    with pytest.raises(ValueError):
        rs.decode({0: coded[0], 1: coded[1], 2: coded[2], 99: coded[3]})     # index out of range
    with pytest.raises(ValueError):
        rs.decode({0: b"ab", 1: b"abc", 2: b"abc", 3: b"abc"})               # unequal lengths
    with pytest.raises(ValueError):
        rs.encode(np.zeros((3, 4), np.uint8))
