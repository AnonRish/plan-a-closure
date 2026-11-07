import json
import warnings
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings("ignore", category=ConvergenceWarning)

from teacher import make_two_spirals, train_teacher, confirm_task_is_nontrivial
from extraction import random_extraction, active_extraction, evaluate_student
from defenses import NoisyTeacher, legitimate_user_cost

BOUNDS = 1.3


def input_sampler(n, rng):
    return rng.uniform(-BOUNDS, BOUNDS, size=(n, 2))


def sweep(teacher, X_test, y_test, budgets, strategy, n_seeds=5):
    results = {b: {"fidelity": [], "accuracy": []} for b in budgets}
    for seed in range(n_seeds):
        rng = np.random.default_rng(1000 + seed)
        for b in budgets:
            if strategy == "random":
                student = random_extraction(teacher, input_sampler, b, rng)
            else:
                student = active_extraction(teacher, input_sampler, b, rng)
            m = evaluate_student(student, teacher, X_test, y_test)
            results[b]["fidelity"].append(m["fidelity"])
            results[b]["accuracy"].append(m["accuracy"])
    return {
        b: {
            "fidelity_mean": float(np.mean(v["fidelity"])), "fidelity_std": float(np.std(v["fidelity"])),
            "accuracy_mean": float(np.mean(v["accuracy"])), "accuracy_std": float(np.std(v["accuracy"])),
        } for b, v in results.items()
    }


def plot_boundary(ax, model, title, X_ref=None, y_ref=None):
    xx, yy = np.meshgrid(np.linspace(-BOUNDS, BOUNDS, 220), np.linspace(-BOUNDS, BOUNDS, 220))
    grid = np.column_stack([xx.ravel(), yy.ravel()])
    Z = model.predict(grid).reshape(xx.shape)
    ax.contourf(xx, yy, Z, levels=[-0.5, 0.5, 1.5], colors=["#E9E6DC", "#4A93A6"], alpha=0.55)
    if X_ref is not None:
        ax.scatter(X_ref[y_ref == 0, 0], X_ref[y_ref == 0, 1], s=3, color="#C05B48", alpha=0.6)
        ax.scatter(X_ref[y_ref == 1, 0], X_ref[y_ref == 1, 1], s=3, color="#1C1F26", alpha=0.6)
    ax.set_title(title, fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    X, y = make_two_spirals(n_per_class=800, rng=rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

    linear_acc = confirm_task_is_nontrivial(X_train, y_train, X_test, y_test)
    teacher = train_teacher(X_train, y_train)
    from sklearn.metrics import accuracy_score
    teacher_acc = accuracy_score(y_test, teacher.predict(X_test))
    print(f"linear baseline accuracy: {linear_acc:.3f}  |  teacher accuracy: {teacher_acc:.3f}")

    budgets = [30, 60, 120, 250, 500, 1000]
    print("\n=== Random-query extraction ===")
    random_results = sweep(teacher, X_test, y_test, budgets, "random", n_seeds=3)
    for b in budgets:
        r = random_results[b]
        print(f"  budget={b:5d}  fidelity={r['fidelity_mean']:.3f}±{r['fidelity_std']:.3f}  accuracy={r['accuracy_mean']:.3f}±{r['accuracy_std']:.3f}")

    print("\n=== Active (uncertainty-sampling) extraction ===")
    active_results = sweep(teacher, X_test, y_test, budgets, "active", n_seeds=3)
    for b in budgets:
        r = active_results[b]
        print(f"  budget={b:5d}  fidelity={r['fidelity_mean']:.3f}±{r['fidelity_std']:.3f}  accuracy={r['accuracy_mean']:.3f}±{r['accuracy_std']:.3f}")

    # query efficiency: how many queries does each strategy need to reach 90% fidelity?
    def queries_to_reach(results, target, key="fidelity_mean"):
        for b in budgets:
            if results[b][key] >= target:
                return b
        return None

    for target in [0.80, 0.90, 0.95]:
        r_b = queries_to_reach(random_results, target)
        a_b = queries_to_reach(active_results, target)
        print(f"\nqueries to reach {target:.0%} fidelity: random={r_b}  active={a_b}")

    # --- defense sweep ---
    print("\n=== Noise defense: extraction fidelity vs. flip probability (budget=500, random strategy) ===")
    defense_results = {}
    for flip_p in [0.0, 0.05, 0.10, 0.20, 0.30]:
        fids, costs = [], []
        for seed in range(3):
            rng_d = np.random.default_rng(2000 + seed)
            noisy = NoisyTeacher(teacher, flip_p, rng_d)
            student = random_extraction(noisy, input_sampler, 500, rng_d)
            m = evaluate_student(student, teacher, X_test, y_test)  # fidelity measured against the TRUE teacher
            fids.append(m["fidelity"])
            costs.append(legitimate_user_cost(teacher, noisy, X_test))
        defense_results[flip_p] = {"fidelity_mean": float(np.mean(fids)), "legit_cost_mean": float(np.mean(costs))}
        print(f"  flip_prob={flip_p:.2f}  extraction_fidelity={np.mean(fids):.3f}  legitimate_user_disagreement_rate={np.mean(costs):.3f}")

    # --- plots ---
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.3))
    plot_boundary(axes[0], teacher, "Teacher (true boundary)", X_test, y_test)
    for ax, b in zip(axes[1:], [120, 500]):
        rng_p = np.random.default_rng(1000)
        s = random_extraction(teacher, input_sampler, b, rng_p)
        plot_boundary(ax, s, f"Random extraction, N={b}")
    rng_p = np.random.default_rng(1000)
    s_active = active_extraction(teacher, input_sampler, 120, rng_p)
    plot_boundary(axes[3], s_active, "Active extraction, N=120")
    fig.suptitle("Student decision boundaries recovered under query budget", fontsize=12)
    fig.tight_layout()
    fig.savefig("boundaries.png", dpi=170, facecolor="white")
    plt.close(fig)
    print("\nSaved boundaries.png")

    fig, ax = plt.subplots(figsize=(7, 5))
    r_fid = [random_results[b]["fidelity_mean"] for b in budgets]
    a_fid = [active_results[b]["fidelity_mean"] for b in budgets]
    ax.plot(budgets, r_fid, "o-", color="#C05B48", label="random queries")
    ax.plot(budgets, a_fid, "o-", color="#4A93A6", label="active (uncertainty) queries")
    ax.axhline(teacher_acc, color="#5B594F", linestyle=":", label="teacher's own accuracy ceiling")
    ax.set_xscale("log")
    ax.set_xlabel("query budget")
    ax.set_ylabel("fidelity to teacher")
    ax.set_title("Extraction fidelity vs. query budget")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig("fidelity_vs_budget.png", dpi=170, facecolor="white")
    plt.close(fig)
    print("Saved fidelity_vs_budget.png")

    with open("results.json", "w") as f:
        json.dump({
            "linear_baseline_accuracy": linear_acc, "teacher_accuracy": teacher_acc,
            "random": {str(k): v for k, v in random_results.items()},
            "active": {str(k): v for k, v in active_results.items()},
            "defense": {str(k): v for k, v in defense_results.items()},
        }, f, indent=2)
    print("Saved results.json")
