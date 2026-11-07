"""The Verification Plan's evaluation metrics as a checked scorecard (Plan A row VP-2.8).

The plan rates every verification proposal on its "five key verification metrics" and lists six: the assurance curve,
execution difficulty, preparation required, privacy level, economic cost and scope. Only the assurance curve is a formula
(coverage = 1 - F*, confidence = 1 - exp(-N_ver F*)); the rest are judgments. This module makes each metric a typed field
with the plan's own wording, computes the one the plan defines, refuses a scorecard with a missing or out-of-range field,
and records scores for the mechanisms in this repository so that a reviewer can dispute a specific number rather than a
paragraph. The scores are judgments written down for review, not measurements; `basis` says what each rests on.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .assurance import confidence_at_coverage

DEFINITIONS = {
    "assurance_curve": "The assurance curve captures information about the level of coverage (confidence that a violation "
                       "affecting more than 1 - coverage of the work would be caught).",
    "execution_difficulty": "How difficult would it be to implement the verification solution correctly?",
    "preparation_required": "How much research time is required to implement the verification solution.",
    "privacy_level": "To what extent the verification proposal requires private information to be disclosed.",
    "economic_cost": "How much overall economic value is lost by implementing the verification solution.",
    "scope": "Does the verification solution just check for inference-only, or arbitrary AI workloads?",
}
DIFFICULTY = ("low", "medium", "high")
PRIVACY = ("none", "aggregate-telemetry", "hashes-and-samples", "plaintext")   # what the verifier sees, least first
SCOPE = ("inference-only", "arbitrary-workloads", "supporting")


@dataclass(frozen=True)
class Scorecard:
    mechanism: str
    n_ver: float                     # independent verification samples behind the assurance curve (0: no sampling)
    execution_difficulty: str
    preparation_years: float         # research time before a field deployment, in years
    privacy_level: str
    economic_cost_frac: float        # share of the cluster's economic output lost (overhead, downtime)
    scope: str
    basis: str                       # what in this repository or the plan each number rests on

    def assurance(self, coverage: float = 0.999) -> float:
        """Confidence that a violation touching more than 1 - coverage of the work is caught (plan, Appendix A.3)."""
        return confidence_at_coverage(self.n_ver, coverage) if self.n_ver > 0 else 0.0


def validate(card: Scorecard) -> list:
    errs = []
    if card.execution_difficulty not in DIFFICULTY:
        errs.append(f"{card.mechanism}: execution_difficulty must be one of {DIFFICULTY}")
    if card.privacy_level not in PRIVACY:
        errs.append(f"{card.mechanism}: privacy_level must be one of {PRIVACY}")
    if card.scope not in SCOPE:
        errs.append(f"{card.mechanism}: scope must be one of {SCOPE}")
    if not 0.0 <= card.economic_cost_frac <= 1.0:
        errs.append(f"{card.mechanism}: economic_cost_frac must lie in [0, 1]")
    if card.preparation_years < 0 or card.n_ver < 0:
        errs.append(f"{card.mechanism}: preparation_years and n_ver must be non-negative")
    if not card.basis.strip():
        errs.append(f"{card.mechanism}: every scorecard needs a basis")
    return errs


CARDS = (
    Scorecard("tap and sampled recomputation (the plan's retrofit)", 10_000, "medium", 1.0, "hashes-and-samples", 0.01,
              "inference-only", "Plan A Appendix A: N_ver = 10,000 at a 1% recomputation budget; gateway.py, taphash.py"),
    Scorecard("energy and busy-time closure (this repository)", 0, "medium", 0.5, "aggregate-telemetry", 0.002,
              "inference-only", "no sampling: every window is accounted; cost is the probe and trial time on a node "
                                "(docs/HARDWARE_CONFIG.md); detection is the closure gap, not an assurance curve"),
    Scorecard("gateway with weight whitelist", 10_000, "high", 2.0, "hashes-and-samples", 0.01, "inference-only",
              "RFD 017's SNG and SRC; gateway.py; a gateway device has to be built and isolated"),
    Scorecard("hashing tap", 10_000, "high", 2.0, "hashes-and-samples", 0.001, "inference-only",
              "taphash.py; tap output is 32 bytes per group; the FPGA or SmartNIC device does not exist yet"),
    Scorecard("memory-residency challenges", 1_000, "medium", 1.0, "none", 0.005, "supporting",
              "state.py; the stream is the verifier's own data; cost is the challenge time"),
    Scorecard("training-cadence detector (defence in depth)", 0, "low", 0.2, "aggregate-telemetry", 0.0, "supporting",
              "cadence.py; passive power telemetry; a detector with a calibrated false-alarm rate, not a bound"),
)


def table(cards=CARDS, coverage: float = 0.999) -> str:
    rows = ["| mechanism | assurance at %.1f%% coverage | execution difficulty | preparation (years) | privacy level | "
            "economic cost | scope | basis |" % (100 * coverage), "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in cards:
        a = c.assurance(coverage)
        rows.append(f"| {c.mechanism} | {('%.4f' % a) if c.n_ver else 'n/a (no sampling)'} | {c.execution_difficulty} | "
                    f"{c.preparation_years:g} | {c.privacy_level} | {100 * c.economic_cost_frac:.1f}% | {c.scope} | {c.basis} |")
    return "\n".join(rows)


def as_dicts(cards=CARDS) -> list:
    return [{**asdict(c), "assurance_at_99.9pct": c.assurance(0.999)} for c in cards]
