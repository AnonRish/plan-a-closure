"""
generators.py

The threat model: an AI system's output channel is bandwidth-capped (per the
Transparency Plan) specifically to bound how much could leak even in the
worst case. Model weights are orders of magnitude bigger than the cap allows
in one shot, so exfiltrating them means smuggling compressed/quantized
fragments across MANY outputs over time, disguised as normal-looking
content. This module generates three kinds of per-output text:

CLEAN         -- natural-language-like, sampled from real unigram English
                 letter frequencies (a real, citable distribution, not
                 invented -- see ENGLISH_FREQS below).
RAW_PAYLOAD   -- what compressed/quantized weight bytes look like once
                 base64-encoded to survive a text channel: close to uniform
                 over the base64 alphabet, because "compressed" and
                 "close to incompressible/high-entropy" are close to the
                 same thing by construction.
DISGUISED_PAYLOAD -- payload characters resampled from the SAME frequency
                 distribution as clean text -- simulating what a "mimic
                 function"-style encoder (Wayner 1992; the same idea behind
                 modern linguistic steganography) would produce at the
                 unigram level, without implementing the actual reversible
                 encoding machinery. This is deliberately the best case for
                 the attacker, worst case for a unigram-based detector --
                 see README for what this does and doesn't prove.
"""

import math
import numpy as np

# Standard unigram English letter frequencies (%), a well-established table
# (Shannon-era, widely reproduced in cryptography references), renormalized
# below to sum to 1 within the letter budget.
ENGLISH_LETTER_FREQS_PCT = {
    'e': 12.70, 't': 9.06, 'a': 8.17, 'o': 7.51, 'i': 6.97, 'n': 6.75,
    's': 6.33, 'h': 6.09, 'r': 5.99, 'd': 4.25, 'l': 4.03, 'c': 2.78,
    'u': 2.76, 'm': 2.41, 'w': 2.36, 'f': 2.23, 'g': 2.02, 'y': 1.97,
    'p': 1.93, 'b': 1.29, 'v': 0.98, 'k': 0.77, 'j': 0.15, 'x': 0.15,
    'q': 0.10, 'z': 0.07,
}
SPACE_FRACTION = 0.18  # typical fraction of characters that are spaces in English text

BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _build_clean_distribution():
    letters = list(ENGLISH_LETTER_FREQS_PCT.keys()) + [' ']
    letter_total = sum(ENGLISH_LETTER_FREQS_PCT.values())
    probs = [ENGLISH_LETTER_FREQS_PCT[c] / letter_total * (1 - SPACE_FRACTION) for c in letters[:-1]]
    probs.append(SPACE_FRACTION)
    probs = np.array(probs)
    probs = probs / probs.sum()
    return letters, probs


CLEAN_ALPHABET, CLEAN_PROBS = _build_clean_distribution()


def shannon_entropy_bits(probs):
    probs = np.asarray(probs)
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


CLEAN_ENTROPY_BITS_PER_CHAR = shannon_entropy_bits(CLEAN_PROBS)               # ~4.1 bits/char, computed not assumed
RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR = math.log2(len(BASE64_ALPHABET))          # exactly 6.0, uniform over 64 symbols


def generate_clean_chunk(rng, length):
    return "".join(rng.choice(CLEAN_ALPHABET, size=length, p=CLEAN_PROBS))


def generate_raw_payload_chunk(rng, length):
    """Undisguised: uniform over the base64 alphabet, as real compressed bytes would be."""
    return "".join(rng.choice(list(BASE64_ALPHABET), size=length))


def generate_disguised_payload_chunk(rng, length):
    """Best-case-for-attacker: payload characters resampled from the clean
    distribution. Carries real (compressed) information in principle, via a
    mimic-style reversible encoding this module does not implement -- only
    its resulting unigram statistics are simulated, which is what a
    unigram-based detector can see regardless of encoding mechanics."""
    return "".join(rng.choice(CLEAN_ALPHABET, size=length, p=CLEAN_PROBS))


def generate_session(rng, n_outputs, injection_rate, payload_kind, chunk_length=180):
    """Returns (chunks, true_labels). payload_kind in {'raw', 'disguised', None}.
    injection_rate is ignored if payload_kind is None (pure clean session)."""
    chunks, labels = [], []
    for _ in range(n_outputs):
        is_payload = payload_kind is not None and rng.random() < injection_rate
        if not is_payload:
            chunks.append(generate_clean_chunk(rng, chunk_length))
            labels.append(0)
        elif payload_kind == "raw":
            chunks.append(generate_raw_payload_chunk(rng, chunk_length))
            labels.append(1)
        else:
            chunks.append(generate_disguised_payload_chunk(rng, chunk_length))
            labels.append(1)
    return chunks, labels
