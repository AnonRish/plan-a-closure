# Training-vs-inference workload discriminator

The software-only slice of AI Security Forum RFD 027 ("Training vs Inference Workload
Discrimination"). The full RFD wants power draw and EM emissions too — real signals,
but ones that need real hardware I don't have. This is the part of it that's visible
from network traffic alone: does a compute unit's traffic pattern look like
distributed training (gradient sync) or inference serving (request/response), without
ever looking inside the payload.

## Why this, and why now

Arbiter's Registry tracks *declared* compute per unit and audits whether declared
matches true capacity. It has no way to check whether a unit *doing* what it says
it's doing — a lab registered as running inference could quietly be training instead,
which is exactly the kind of compute-cap evasion Capability Scaling Strategy and
Covert AI Projects both worry about. This is the natural next signal for that gap:
not "how much compute," but "what is it actually doing with it."

## The three features

- **inter_event_cv** — regularity of event timing. Training's gradient-sync cadence
  is regular (low CV); inference's request arrivals are irregular (high CV).
- **log_symmetry_ratio** — log(bytes sent / bytes received). AllReduce is symmetric
  (near 0); inference is a short upload, long download (well below 0).
- **burst_size_cv** — how much each exchange's size varies. Same model's gradients
  every step (low CV) vs. different queries every time (high CV).

Three independently-motivated, auditor-explainable signals — not a black box.

## What the numbers actually show

A logistic regression on 600 synthetic sessions (300/class, 70/30 split) gets
accuracy/precision/recall/ROC-AUC all at **1.000** — which is the *uninteresting*
number here: the two classes are qualitatively very different by construction in
this synthetic generator, so clean separation on non-adversarial data is expected,
not a real-world claim.

The real finding is the adversarial comparison. Against inference traffic
deliberately timed to look training-regular (a load-testing script hitting fixed
intervals — a genuine, plausible evasion attempt), the full 3-feature classifier
holds at **94.0% accuracy** (18/300 misclassified). A classifier using *only* timing
regularity — the single most obvious signal, and the one RFD 027 leads with —
collapses to **0% accuracy** on that exact same adversarial set: every single
disguised session is fooled. The byte-asymmetry features are what's actually load-
bearing once an adversary controls the easy signal. `feature_space.png` shows this
directly: the adversarial points shift into training's timing cluster on the x-axis
but stay in inference's territory on the y-axis.

## Running it

```
pip install scikit-learn numpy matplotlib pytest
python3 run_evaluation.py                        # trains, evaluates, prints all of the above, saves plots
python3 -m pytest test_workload_discriminator.py -v   # 12 tests
```

## What this does not do

Every number above is against **synthetic data built from qualitative domain
knowledge of how AllReduce and inference serving actually behave** — not captured
real traffic. I have no real labeled network captures from training or inference
clusters, and getting real-world accuracy figures needs them. Real deployment would
also face adversaries smarter than "fake the timing" — e.g. deliberately padding
requests to fake symmetry, or literally interleaving small training steps between
inference-shaped bursts. This is a first-cut, honestly-scoped starting point and a
demonstration of *why* multi-signal beats single-signal, not a finished detector.
