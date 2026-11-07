"""
extraction.py

Two query strategies an attacker with a fixed query budget N could use to
build a synthetic training set from a black-box teacher:

RANDOM      -- sample N random inputs, query the teacher, train a student
               on the (input, teacher_label) pairs. The naive approach.

ACTIVE      -- uncertainty-sampling active learning (Settles, 2009): start
               from a small random seed, then repeatedly query the teacher
               on whichever candidate inputs the CURRENT student is least
               sure about, retrain, repeat. Standard technique for getting
               more signal per label in ordinary ML -- the red-team question
               is whether it also makes black-box extraction more
               query-efficient, which is exactly what a sophisticated
               covert distillation effort would be expected to use instead
               of naive random sampling.

Both measure two different things, which matter for different reasons:
FIDELITY  -- fraction of test points where student's prediction matches
             the TEACHER's prediction (mimicry, whether or not either is
             "correct" against ground truth -- this is what distillation
             is actually trying to achieve).
ACCURACY  -- fraction where the student matches the TRUE label (whether
             real capability, not just mimicry of teacher's mistakes too,
             transferred).
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score


def make_student():
    """lbfgs converges faster and to better fidelity than adam for a network
    this size fitting an already-smoothed target (the teacher's own
    predictions) -- profiled, not guessed; adam left students undertrained
    at a budget that made the whole sweep too slow to run."""
    return MLPClassifier(hidden_layer_sizes=(48, 48), max_iter=800, random_state=0, solver="lbfgs", alpha=1e-4)


def random_extraction(teacher, input_sampler, budget, rng):
    X_query = input_sampler(budget, rng)
    y_query = teacher.predict(X_query)
    if len(np.unique(y_query)) < 2:
        return None  # can't train a classifier on one class; caller handles this
    student = make_student()
    student.fit(X_query, y_query)
    return student


def active_extraction(teacher, input_sampler, budget, rng, seed_frac=0.15, pool_size=800, batch_frac=0.12):
    seed_n = max(4, int(budget * seed_frac))
    X_seed = input_sampler(seed_n, rng)
    y_seed = teacher.predict(X_seed)
    X_have, y_have = X_seed, y_seed

    batch_n = max(2, int(budget * batch_frac))
    remaining = budget - seed_n

    while remaining > 0:
        if len(np.unique(y_have)) < 2:
            # can't estimate uncertainty without both classes yet; query more randomly
            take = min(batch_n, remaining)
            X_new = input_sampler(take, rng)
        else:
            student = make_student()
            student.fit(X_have, y_have)
            pool = input_sampler(pool_size, rng)
            probs = student.predict_proba(pool)[:, 1]
            uncertainty = np.abs(probs - 0.5)   # smaller = closer to 0.5 = more uncertain
            take = min(batch_n, remaining)
            chosen_idx = np.argsort(uncertainty)[:take]
            X_new = pool[chosen_idx]
        y_new = teacher.predict(X_new)
        X_have = np.vstack([X_have, X_new])
        y_have = np.concatenate([y_have, y_new])
        remaining -= len(X_new)

    if len(np.unique(y_have)) < 2:
        return None
    student = make_student()
    student.fit(X_have, y_have)
    return student


def evaluate_student(student, teacher, X_test, y_test):
    if student is None:
        # degenerate case: couldn't even get both classes: report as chance/majority
        majority = int(round(y_test.mean()))
        student_pred = np.full_like(y_test, majority)
        teacher_pred = teacher.predict(X_test)
    else:
        student_pred = student.predict(X_test)
        teacher_pred = teacher.predict(X_test)
    return {
        "fidelity": float(accuracy_score(teacher_pred, student_pred)),
        "accuracy": float(accuracy_score(y_test, student_pred)),
    }
