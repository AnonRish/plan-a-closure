"""GF(2^8) with reduction polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D) and generator 2."""
from __future__ import annotations

import numpy as np

POLY = 0x11D

EXP = np.zeros(512, dtype=np.uint8)
LOG = np.zeros(256, dtype=np.int32)
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= POLY
EXP[255:510] = EXP[0:255]

#: MUL[a, b] = a * b in GF(256)
MUL = np.zeros((256, 256), dtype=np.uint8)
MUL[1:, 1:] = EXP[LOG[1:, None] + LOG[None, 1:]]

#: INV[a] = a^-1 (INV[0] is 0 and must never be used)
INV = np.zeros(256, dtype=np.uint8)
INV[1:] = EXP[255 - LOG[1:]]


def mul(a: int, b: int) -> int:
    return int(MUL[a, b])


def inv(a: int) -> int:
    if a == 0:
        raise ZeroDivisionError("0 has no inverse in GF(256)")
    return int(INV[a])


def solve(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Solve ``A X = B`` over GF(256): ``A`` is (m, m), ``B`` is (m, S). Raises ``ValueError`` if ``A`` is singular."""
    A = np.array(A, dtype=np.uint8)
    B = np.array(B, dtype=np.uint8)
    m = A.shape[0]
    if A.shape != (m, m) or B.shape[0] != m:
        raise ValueError("shape mismatch")
    for col in range(m):
        pivot = next((r for r in range(col, m) if A[r, col]), None)
        if pivot is None:
            raise ValueError("singular matrix")
        if pivot != col:
            A[[col, pivot]] = A[[pivot, col]]
            B[[col, pivot]] = B[[pivot, col]]
        s = INV[A[col, col]]
        A[col] = MUL[s][A[col]]
        B[col] = MUL[s][B[col]]
        for r in range(m):
            f = A[r, col]
            if r != col and f:
                A[r] ^= MUL[f][A[col]]
                B[r] ^= MUL[f][B[col]]
    return B
