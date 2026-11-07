import json
import numpy as np
import matplotlib.pyplot as plt

from classifier import train_and_evaluate, evaluate_adversarial, evaluate_timing_only_baseline, build_dataset
from features import FEATURE_NAMES

if __name__ == "__main__":
    clf, metrics = train_and_evaluate(seed=0, n_per_class=300)

    print("=== Held-out evaluation (300/class train, 30% held out) ===")
    for k in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
        print(f"  {k:10s} {metrics[k]:.3f}")
    print(f"  confusion matrix [[TN,FP],[FN,TP]] (positive=training): {metrics['confusion_matrix']}")
    print(f"  coefficients: {json.dumps(metrics['coefficients'], indent=2)}")
    print(f"  intercept: {metrics['intercept']:.3f}")

    adv = evaluate_adversarial(clf, n=300, seed=1)
    print("\n=== Adversarial stress test: inference traffic on a training-regular clock ===")
    print(f"  n={adv['n']}, accuracy={adv['accuracy']:.3f}, misclassified as training={adv['misclassified_as_training']}/{adv['n']}")

    baseline = evaluate_timing_only_baseline()
    print("\n=== Comparison: a classifier using ONLY inter_event_cv (timing regularity) ===")
    print(f"  held-out accuracy:   {baseline['held_out_accuracy']:.3f}")
    print(f"  adversarial accuracy: {baseline['adversarial_accuracy']:.3f}  <-- collapses when timing is faked")

    # Feature-space plot: symmetry ratio vs inter-event CV, normal classes + adversarial overlay
    rng = np.random.default_rng(7)
    X, y, _ = build_dataset(150, rng)
    from traffic_gen import generate_adversarial_regular_inference_session
    from features import feature_vector
    adv_sessions = [generate_adversarial_regular_inference_session(rng) for _ in range(150)]
    X_adv = np.array([feature_vector(s) for s in adv_sessions])

    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(X[y == 1, 0], X[y == 1, 1], s=14, alpha=0.55, color="#4A93A6", label="training (true)")
    ax.scatter(X[y == 0, 0], X[y == 0, 1], s=14, alpha=0.55, color="#C9922E", label="inference (true)")
    ax.scatter(X_adv[:, 0], X_adv[:, 1], s=20, alpha=0.75, color="#C05B48", marker="x", label="adversarial inference\n(regular clock, asymmetric bytes)")
    ax.set_xlabel("inter_event_cv  (low = regular cadence)")
    ax.set_ylabel("log_symmetry_ratio  (near 0 = symmetric)")
    ax.set_title("Feature space: the adversarial case has training-like timing\nbut keeps inference-like asymmetry", fontsize=11, loc="left")
    ax.axhline(0, color="#5B594F", linewidth=0.8, linestyle=":")
    ax.legend(fontsize=8.5, loc="upper right")
    fig.tight_layout()
    fig.savefig("feature_space.png", dpi=170, facecolor="white")
    plt.close(fig)
    print("\nSaved feature_space.png")

    with open("results.json", "w") as f:
        json.dump({"held_out": metrics, "adversarial": adv, "timing_only_baseline": baseline}, f, indent=2)
    print("Saved results.json")
