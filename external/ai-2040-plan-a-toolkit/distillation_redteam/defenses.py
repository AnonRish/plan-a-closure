"""
defenses.py

A standard, real mitigation against model extraction: perturb the teacher's
outputs so an attacker's (input, output) pairs are noisier -- degrading the
student they can train -- while trying to keep the cost to LEGITIMATE users
low. This wraps a trained teacher so its .predict() flips each label
independently with probability flip_prob. The tradeoff is the whole point:
this defense does not distinguish attacker traffic from legitimate traffic,
so whatever it costs the attacker, it costs every other user too.
"""

import numpy as np


class NoisyTeacher:
    def __init__(self, teacher, flip_prob, rng):
        self.teacher = teacher
        self.flip_prob = flip_prob
        self.rng = rng

    def predict(self, X):
        clean = self.teacher.predict(X)
        flips = self.rng.random(len(clean)) < self.flip_prob
        noisy = clean.copy()
        noisy[flips] = 1 - noisy[flips]
        return noisy

    def predict_proba(self, X):
        # legitimate callers relying on calibrated probabilities are hurt too --
        # approximate the effect by mixing toward uniform confidence.
        clean = self.teacher.predict_proba(X)
        return clean * (1 - self.flip_prob) + 0.5 * self.flip_prob


def legitimate_user_cost(teacher, noisy_teacher, X_eval):
    """How often does the defended API disagree with the true teacher, for
    an ordinary caller who isn't attacking anything?"""
    clean_pred = teacher.predict(X_eval)
    noisy_pred = noisy_teacher.predict(X_eval)
    return float(np.mean(clean_pred != noisy_pred))
