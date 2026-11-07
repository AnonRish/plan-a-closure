import json
import numpy as np
import matplotlib.pyplot as plt

from detector import (
    train_classifier, calibrate_k, calibrate_threshold, evaluate_detection,
    evaluate_false_positive_rate, run_cusum,
)
from generators import (
    generate_session, CLEAN_ENTROPY_BITS_PER_CHAR, RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR,
)

if __name__ == "__main__":
    print("=== Per-chunk classifier (clean vs raw base64-like payload) ===")
    clf, metrics = train_classifier(seed=0, n_per_class=400)
    print(f"  held-out accuracy={metrics['accuracy']:.3f}  roc_auc={metrics['roc_auc']:.3f}")
    print(f"  coefficients: {json.dumps(metrics['coefficients'], indent=2)}")

    rng = np.random.default_rng(1)
    k = calibrate_k(clf, rng, n_sessions=200, session_len=60)
    print(f"\n=== CUSUM calibration ===\n  slack k = {k:.4f}")

    rng = np.random.default_rng(2)
    h = calibrate_threshold(clf, k, rng, target_fpr=0.05, n_sessions=400, session_len=80)
    print(f"  threshold h (target FPR 5%) = {h:.3f}")

    rng = np.random.default_rng(3)
    achieved_fpr = evaluate_false_positive_rate(clf, k, h, rng, n_sessions=500, session_len=80)
    print(f"  achieved FPR on 500 fresh clean sessions: {achieved_fpr:.3f}")

    print("\n=== Detection vs. RAW (undisguised) payload, at several injection rates ===")
    raw_results = {}
    for rate in [0.05, 0.10, 0.20, 0.30, 0.50]:
        rng = np.random.default_rng(100 + int(rate * 100))
        res = evaluate_detection(clf, k, h, rng, injection_rate=rate, payload_kind="raw", n_sessions=300, session_len=80)
        raw_results[rate] = res
        lat = f"{res['mean_outputs_to_detect']:.1f}" if res['mean_outputs_to_detect'] else "n/a"
        print(f"  injection_rate={rate:.2f}  detection_rate={res['detection_rate']:.3f}  mean_outputs_to_detect={lat}")

    print("\n=== Detection vs. DISGUISED payload (unigram-statistics-matched) ===")
    disguised_results = {}
    for rate in [0.10, 0.30, 0.50, 0.80, 1.0]:
        rng = np.random.default_rng(200 + int(rate * 100))
        res = evaluate_detection(clf, k, h, rng, injection_rate=rate, payload_kind="disguised", n_sessions=300, session_len=80)
        disguised_results[rate] = res
        lat = f"{res['mean_outputs_to_detect']:.1f}" if res['mean_outputs_to_detect'] else "n/a"
        print(f"  injection_rate={rate:.2f}  detection_rate={res['detection_rate']:.3f}  mean_outputs_to_detect={lat}")

    print("\n=== Why: the information-theoretic cost of disguising ===")
    ratio = CLEAN_ENTROPY_BITS_PER_CHAR / RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR
    print(f"  clean-text unigram entropy:  {CLEAN_ENTROPY_BITS_PER_CHAR:.3f} bits/char (computed from the letter-frequency table)")
    print(f"  raw base64 entropy:          {RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR:.3f} bits/char (log2(64), exact)")
    print(f"  max payload rate while matching clean unigram stats: {ratio:.3f}x of raw rate")
    print(f"  i.e. disguising this way needs {1/ratio:.2f}x as many characters (and outputs, and time) for the same payload")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), sharey=True)
    titles = ["Clean session", "30% raw-payload injection", "30% disguised-payload injection"]
    configs = [(0.0, None), (0.30, "raw"), (0.30, "disguised")]
    for ax, title, (rate, kind) in zip(axes, titles, configs):
        rng = np.random.default_rng(42)
        for i in range(12):
            chunks, labels = generate_session(rng, 80, rate, kind)
            trace = run_cusum(clf, chunks, k)
            ax.plot(trace, color="#4A93A6" if kind is None else ("#C05B48" if kind == "raw" else "#C9922E"), alpha=0.5, linewidth=1)
        ax.axhline(h, color="#1C1F26", linestyle="--", linewidth=1, label=f"threshold h={h:.1f}")
        ax.set_title(title, fontsize=10.5)
        ax.set_xlabel("output #")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("CUSUM statistic")
    fig.suptitle("CUSUM traces: raw payload crosses the threshold, disguised payload doesn't", fontsize=11)
    fig.tight_layout()
    fig.savefig("cusum_traces.png", dpi=170, facecolor="white")
    plt.close(fig)
    print("\nSaved cusum_traces.png")

    with open("results.json", "w") as f:
        json.dump({
            "classifier": metrics, "k": k, "h": h, "achieved_fpr": achieved_fpr,
            "raw_payload": {str(k2): v for k2, v in raw_results.items()},
            "disguised_payload": {str(k2): v for k2, v in disguised_results.items()},
            "clean_entropy_bits_per_char": CLEAN_ENTROPY_BITS_PER_CHAR,
            "raw_payload_entropy_bits_per_char": RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR,
            "disguise_bandwidth_ratio": ratio,
        }, f, indent=2)
    print("Saved results.json")
