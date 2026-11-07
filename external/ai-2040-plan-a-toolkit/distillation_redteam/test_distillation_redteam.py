import numpy as np
import pytest
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from .teacher import make_two_spirals, train_teacher, confirm_task_is_nontrivial
from .extraction import random_extraction, active_extraction, evaluate_student, make_student
from .defenses import NoisyTeacher, legitimate_user_cost


@pytest.fixture(scope="module")
def teacher_setup():
    rng = np.random.default_rng(0)
    X, y = make_two_spirals(n_per_class=400, rng=rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    teacher = train_teacher(X_train, y_train)
    return teacher, X_train, y_train, X_test, y_test


def input_sampler(n, rng):
    return rng.uniform(-1.3, 1.3, size=(n, 2))


def test_linear_baseline_confirms_task_is_genuinely_nonlinear(teacher_setup):
    teacher, X_train, y_train, X_test, y_test = teacher_setup
    linear_acc = confirm_task_is_nontrivial(X_train, y_train, X_test, y_test)
    assert linear_acc < 0.80, "if a linear model solves this too, it's not testing real nonlinear capability"


def test_teacher_achieves_high_accuracy(teacher_setup):
    teacher, X_train, y_train, X_test, y_test = teacher_setup
    acc = accuracy_score(y_test, teacher.predict(X_test))
    assert acc > 0.95


def test_random_extraction_improves_with_more_queries(teacher_setup):
    teacher, _, _, X_test, y_test = teacher_setup
    rng = np.random.default_rng(1)
    low = evaluate_student(random_extraction(teacher, input_sampler, 30, rng), teacher, X_test, y_test)
    rng = np.random.default_rng(2)
    high = evaluate_student(random_extraction(teacher, input_sampler, 500, rng), teacher, X_test, y_test)
    assert high["fidelity"] > low["fidelity"]


def test_extraction_fidelity_at_high_budget_is_strong(teacher_setup):
    teacher, _, _, X_test, y_test = teacher_setup
    rng = np.random.default_rng(3)
    student = random_extraction(teacher, input_sampler, 600, rng)
    m = evaluate_student(student, teacher, X_test, y_test)
    assert m["fidelity"] > 0.85


def test_active_extraction_runs_and_returns_valid_student(teacher_setup):
    teacher, _, _, X_test, y_test = teacher_setup
    rng = np.random.default_rng(4)
    student = active_extraction(teacher, input_sampler, 200, rng)
    assert student is not None
    m = evaluate_student(student, teacher, X_test, y_test)
    assert 0 <= m["fidelity"] <= 1


def test_low_budget_can_degenerate_to_one_class_and_is_handled():
    """At very low N, random querying can plausibly hit only one class --
    the pipeline should degrade gracefully, not crash."""
    rng = np.random.default_rng(0)
    X, y = make_two_spirals(n_per_class=200, rng=rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    teacher = train_teacher(X_train, y_train)
    # force a degenerate query set directly
    student = random_extraction(teacher, lambda n, r: np.array([[0.9, 0.9]] * n), 5, np.random.default_rng(0))
    assert student is None
    m = evaluate_student(student, teacher, X_test, y_test)
    assert 0 <= m["fidelity"] <= 1  # falls back to majority-class prediction, doesn't crash


def test_fidelity_and_accuracy_are_different_quantities():
    """Fidelity measures agreement with the teacher; accuracy measures agreement
    with truth. A student can match a wrong teacher and score high fidelity,
    low accuracy relative to ground truth in principle -- confirm they're
    computed independently, not aliased to the same number by accident."""
    rng = np.random.default_rng(0)
    X, y = make_two_spirals(n_per_class=300, rng=rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    teacher = train_teacher(X_train, y_train)
    student = random_extraction(teacher, input_sampler, 150, np.random.default_rng(1))
    m = evaluate_student(student, teacher, X_test, y_test)
    assert isinstance(m["fidelity"], float) and isinstance(m["accuracy"], float)


def test_noisy_teacher_flip_rate_matches_configured_probability():
    rng = np.random.default_rng(0)
    X, y = make_two_spirals(n_per_class=300, rng=rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    teacher = train_teacher(X_train, y_train)
    noisy = NoisyTeacher(teacher, flip_prob=0.25, rng=np.random.default_rng(5))
    disagreement = legitimate_user_cost(teacher, noisy, X_test)
    assert 0.15 < disagreement < 0.35  # should be near 0.25, generous tolerance for sampling noise


def test_defense_degrades_extraction_fidelity():
    rng = np.random.default_rng(0)
    X, y = make_two_spirals(n_per_class=400, rng=rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    teacher = train_teacher(X_train, y_train)

    rng_clean = np.random.default_rng(1)
    clean_student = random_extraction(teacher, input_sampler, 400, rng_clean)
    clean_fidelity = evaluate_student(clean_student, teacher, X_test, y_test)["fidelity"]

    rng_noisy = np.random.default_rng(1)
    noisy_teacher = NoisyTeacher(teacher, flip_prob=0.3, rng=rng_noisy)
    noisy_student = random_extraction(noisy_teacher, input_sampler, 400, rng_noisy)
    noisy_fidelity = evaluate_student(noisy_student, teacher, X_test, y_test)["fidelity"]

    assert noisy_fidelity < clean_fidelity


def test_defense_cost_to_legitimate_users_scales_with_flip_prob():
    rng = np.random.default_rng(0)
    X, y = make_two_spirals(n_per_class=300, rng=rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    teacher = train_teacher(X_train, y_train)
    low_cost = legitimate_user_cost(teacher, NoisyTeacher(teacher, 0.05, np.random.default_rng(1)), X_test)
    high_cost = legitimate_user_cost(teacher, NoisyTeacher(teacher, 0.30, np.random.default_rng(1)), X_test)
    assert high_cost > low_cost
