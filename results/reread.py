"""Re-read a hardware run on record from its bundle: every number docs/DEVIATIONS.md quotes for runs 4 and 5.

    python results/reread.py results/shakedown-2026-11-08-kaggle-t4-run5
    python results/reread.py results/shakedown-2026-11-08-colab-t4-run4

It checks the bundle's SHA-256 against the folder's README, unpacks it into a temporary folder (closure.tier0.unpack:
plain files only, nothing in it is run), and writes three files beside the bundle:

  physics.json                what the GPU did at each requested load level and what each hidden load did to it
  results_posthoc_link.json   the link analysis (amendment v0.6) applied to this run's raw data: a POST HOC reading,
                              because that analysis was chosen after these data were seen
  reread.json                 the registered analysis reproduced from the raw data, its false alarms by load level, the
                              post hoc reading's headline numbers, and an approximate check of the time bound

Everything here describes the run; none of it decides anything. The pre-registered reading of each run is the
results.json inside its bundle.
"""
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

from closure import physics, tier0
from closure.cli import main
from closure.criteria import evaluate


def _most_common_level(W, block):
    lev = W["lev"][(W["src"] == "aud") & (W["blk"] == block)]
    return float(Counter(lev.tolist()).most_common(1)[0][0])


def reread(folder: Path) -> dict:
    bundle = folder / "tier0_bundle.tar.gz"
    sha = re.search(r"sha256 `([0-9a-f]{64})`", (folder / "README.md").read_text(encoding="utf-8")).group(1)
    with tempfile.TemporaryDirectory() as tmp:
        root = tier0.unpack(bundle, Path(tmp) / "bundle", sha)
        run = next(root.glob("T1-*"))
        signed = json.loads((run / "results.json").read_text())
        alpha = json.loads((run / "prereg.json").read_text())["cfg"]["alpha"]
        assert main(["verify", str(run)]) == 0

        # 1. the registered analysis, from the raw data
        again_path = Path(tmp) / "again.json"
        assert main(["reanalyze", "--run", str(run), "--out", str(again_path)]) == 0
        again = json.loads(again_path.read_text())
        same = [k for k in signed if signed[k] == again.get(k)]
        cfg, W, note = physics.windows(run)
        null = [b for b, kind in enumerate(again["blocks"]["kind"]) if kind == "none"]
        by_level = {}
        for b in null:
            lv = _most_common_level(W, b)
            k, n = by_level.get(lv, (0, 0))
            by_level[lv] = (k + bool(again["blocks"]["flag_combined"][b]), n + 1)
        ev = evaluate(again, alpha)
        registered = {"keys_identical_to_the_signed_results": sorted(same),
                      "keys_that_differ": sorted(k for k in signed if k not in same),
                      "false_alarms": again["false_positive"]["combined"],
                      "false_alarms_by_most_common_requested_level": {f"{lv:g}": list(v) for lv, v in sorted(by_level.items())},
                      "threshold_method_of_the_combined_test": again["methods_used"]["combined"],
                      "outcome": ev["outcome"], "why": ev["why"]}

        # 2. physics
        rep = physics.report(run)
        (folder / "physics.json").write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")

        # 3. the link analysis, post hoc
        link_path = folder / "results_posthoc_link.json"
        assert main(["reanalyze", "--run", str(run), "--analysis", "link", "--out", str(link_path)]) == 0
        res = json.loads(link_path.read_text())
        ev = evaluate(res, alpha)
        det = res["detection_at_or_above_fraction"]
        post = {"status": res["status"], "threshold_method": res["methods_used"]["combined"],
                "reference_blocks": res["link"]["reference_blocks"],
                "false_alarms": res["false_positive"]["combined"],
                "false_alarms_energy_alone": res["false_positive"]["energy"]["k"],
                "false_alarms_busy_alone": res["false_positive"]["busy"]["k"],
                "detection_at_5_percent_or_more": det["0.05"]["pooled_nonslack"],
                "detection_at_2_percent_or_more": det["0.02"]["pooled_nonslack"],
                "closure_gap_fraction": res["closure_gap_fraction"],
                "slack_inflated_gap_fraction": res["slack"]["slack_inflated_gap_fraction"],
                "block_residual_sd": res["link"]["block_residual_sd"],
                "partial_load_slack": res["link"]["partial_load_slack"],
                "energy_bound_coverage_against_the_labels": res["bound"]["coverage_nonslack"],
                "energy_floor_bound_coverage_against_the_labels": res["bound"]["coverage_floor_bound"],
                "H1.1": ev["H1.1"]["holds"], "H1.2": ev["H1.2"]["holds"], "H1.4": ev["H1.4"]["holds"],
                "H1.4_basis": ev["H1.4"]["basis"], "outcome": ev["outcome"], "why": ev["why"]}

        # 4. the time bound against an approximate truth. These runs did not count the seconds their hidden load ran
        # (0.8.0 does), so the truth is taken as the busy share each label added on an otherwise idle GPU in the same
        # run, for the seconds the load was on. Labels never seen on an idle GPU are left out.
        solo = {r["label_fraction"]: (r["busy_share_added"], r["watts_added"]) for r in rep["hidden_load_on_an_idle_gpu"]}
        blocks = res["blocks"]
        aud = W["src"] == "aud"
        rows = []
        for b, kind in enumerate(blocks["kind"]):
            m = aud & (W["blk"] == b) & (W["hid"] > 0)
            frac = float(blocks["frac"][b] or 0.0)
            if kind == "none" or not m.any() or frac not in solo:
                continue
            on = float(W["dur"][m].sum())
            rows.append((on * solo[frac][0], on * solo[frac][1], blocks["ub_busy_s"][b], blocks["ub_busy_floor_s"][b],
                         blocks["ub_energy_j"][b], blocks["ub_energy_floor_j"][b]))
        approx = None
        if rows:
            hs, he, ub, ubf, ue, uef = map(np.array, zip(*rows))
            approx = {"hidden_blocks_with_a_label_seen_on_an_idle_gpu": len(rows),
                      "time_bound_calibrated_coverage": float(np.mean(ub >= hs)),
                      "time_bound_floor_coverage": float(np.mean(ubf >= hs)),
                      "time_bound_calibrated_median_bound_over_truth": float(np.median(ub / hs)),
                      "time_bound_floor_median_bound_over_truth": float(np.median(ubf / hs)),
                      "energy_bound_calibrated_coverage_of_solo_energy": float(np.mean(ue >= he)),
                      "energy_bound_floor_coverage_of_solo_energy": float(np.mean(uef >= he)),
                      "truth": "busy share and watts each label added on an otherwise idle GPU in this run, times the "
                               "seconds the load was on; approximate, because the run did not count hidden seconds"}
    out = {"bundle_sha256": sha, "trial": run.name, "levels": note, "registered_analysis_from_the_raw_data": registered,
           "link_analysis_post_hoc": post, "bounds_against_an_approximate_truth_post_hoc": approx}
    (folder / "reread.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["."]:
        folder = Path(arg).resolve()
        assert hashlib.sha256((folder / "tier0_bundle.tar.gz").read_bytes()).hexdigest() in (folder / "README.md").read_text()
        print(json.dumps(reread(folder), indent=2))
