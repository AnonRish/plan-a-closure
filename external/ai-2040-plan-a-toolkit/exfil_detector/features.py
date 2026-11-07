"""
features.py

Two features per output chunk:

empirical_entropy   -- Shannon entropy of the chunk's own character
                        distribution, in bits/char. Estimated from the chunk
                        itself (not the generator's true distribution --
                        a real detector never gets to see that).
base64_fraction      -- fraction of characters drawn from the base64
                        alphabet (letters+digits+/+), which is close to 1
                        for base64-encoded payload and close to (26+space)/64
                        coverage for English text, but with a very different
                        SHAPE of usage -- entropy is what actually separates
                        them; this is a cheap complementary signal.
"""

import math
from collections import Counter

from .generators import BASE64_ALPHABET

BASE64_SET = set(BASE64_ALPHABET)


def empirical_entropy_bits(chunk: str) -> float:
    if not chunk:
        return 0.0
    counts = Counter(chunk)
    n = len(chunk)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def base64_fraction(chunk: str) -> float:
    if not chunk:
        return 0.0
    return sum(1 for ch in chunk if ch in BASE64_SET) / len(chunk)


FEATURE_NAMES = ["empirical_entropy", "base64_fraction"]


def feature_vector(chunk: str):
    return [empirical_entropy_bits(chunk), base64_fraction(chunk)]
