"""
teacher.py

Covert AI Projects' "distillation red-team" idea is: simulate a covert actor
trying to extract a frontier model's capability through nothing but API
queries, and measure how much actually transfers. I have no access to a real
frontier model or GPU compute in this environment, so this is NOT that.

What it is: the two-spirals problem -- a real, decades-old benchmark from
the neural-network literature (Lang & Witbrock 1988), specifically famous
for being unsolvable by anything without genuine representational capacity.
A linear model gets ~50% (chance). A model with real capacity gets ~99%+.
That gap is a real, honest stand-in for "the teacher has non-trivial
capability worth stealing" -- the query-budget extraction mechanics below
are the actual generalizable content, whatever the underlying model is.
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score


def make_two_spirals(n_per_class=800, noise=0.045, turns=1.8, rng=None):
    rng = rng or np.random.default_rng(0)
    n = n_per_class
    theta = np.sqrt(rng.uniform(0, 1, n)) * turns * 2 * np.pi
    r = theta / (turns * 2 * np.pi)  # normalized radius in [0, 1], grows with theta

    def spiral(theta, r, rotate_rad):
        x = r * np.cos(theta + rotate_rad) + rng.normal(0, noise, len(theta))
        y = r * np.sin(theta + rotate_rad) + rng.normal(0, noise, len(theta))
        return x, y

    x0, y0 = spiral(theta, r, 0.0)
    x1, y1 = spiral(theta, r, np.pi)  # second arm rotated 180 degrees
    X = np.vstack([np.column_stack([x0, y0]), np.column_stack([x1, y1])])
    y = np.concatenate([np.zeros(n), np.ones(n)])
    idx = rng.permutation(len(X))
    return X[idx], y[idx]


def train_teacher(X_train, y_train, seed=0):
    """A model with real capacity for this task -- an MLP, not a linear model.
    early_stopping=False is deliberate: two-spirals is known to need sustained
    training before loss drops sharply as the network finds the twisted
    boundary; naive early stopping cuts this off well before convergence."""
    clf = MLPClassifier(hidden_layer_sizes=(128, 128), max_iter=3000, random_state=seed,
                         early_stopping=False, learning_rate_init=0.001, alpha=1e-5)
    clf.fit(X_train, y_train)
    return clf


def confirm_task_is_nontrivial(X_train, y_train, X_test, y_test, seed=0):
    """Sanity check the whole premise: a linear model should do close to
    chance, so that teacher accuracy reflects real nonlinear capability,
    not a task any model would ace anyway."""
    linear = LogisticRegression(max_iter=1000, random_state=seed).fit(X_train, y_train)
    return float(accuracy_score(y_test, linear.predict(X_test)))
