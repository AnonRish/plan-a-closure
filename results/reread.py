"""Re-read a hardware run on record from its bundle or bundles: every number docs/DEVIATIONS.md quotes for runs 4 to 8.

    python results/reread.py results/shakedown-2026-11-08-colab-t4-run4           runs 4 and 5 (0.7.0, straight line)
    python results/reread.py results/shakedown-2026-11-08-kaggle-t4-run5
    python results/reread.py results/shakedown-2026-11-11-kaggle-t4-runs6-7       runs 6 and 7 (0.8.0, one campaign)
    python results/reread.py results/shakedown-2026-11-12-colab-t4-run8           run 8 (0.8.0)

It checks each bundle's SHA-256 against the folder's README, unpacks it into a temporary folder (closure.tier0.unpack:
plain files only, nothing in it is run), checks its evidence (`closure verify`), and writes beside the bundle:

  physics.json                what the GPU did at each requested load level and what each hidden load did to it
                              (`gpu0-physics.json` and so on where a folder holds several bundles)
  reread.json                 the registered analysis reproduced from the raw data, and what the raw data add

For runs 4 and 5 (registered analysis: the straight line) reread.json also holds the false alarms by load level, the
headline numbers of a POST HOC reading with the link analysis (results_posthoc_link.json; that analysis was chosen
after those data were seen) and an approximate check of the time bound.

For runs from 0.8.0 on (registered analysis: link, amendment v0.6) it holds, per trial: how closely the signed results
are reproduced, the decision rules read off them, the threshold and the reference scores that set it, every false
alarm and every missed hidden block with the load the GPU was under, the same split between blocks with the GPU flat
out and the rest, the throughput of a flat-out GPU, the clock the trial locked against the clock amendment v0.7
would lock, and the decision rules under the link-full analysis of amendment v0.7 (c): a POST HOC reading for runs 6
to 8, which were made before that analysis existed. Where the bundles are one declared campaign it pools them
(`closure pool`), checks the pooled reading that came back with them, and pools the link-full readings too.

Everything here describes the runs; none of it decides anything. The pre-registered reading of each trial is the
results.json inside its bundle, and of a campaign the pooled reading of its trials.
"""
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

from closure import link, physics, tier0
from closure.cli import _load_run, main
from closure.criteria import evaluate
from closure.trial import block_capacity_j, calibrate


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


FULL = "link-full"      # the comparison analysis of amendment v0.7 (c)


def _rel_diff(a, b, path=""):
    """(largest relative difference between two JSON trees' numbers, paths where anything that is not a number
    differs)."""
    worst, other = 0.0, []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                other.append(f"{path}/{k}")
                continue
            w, o = _rel_diff(a[k], b[k], f"{path}/{k}")
            worst, other = max(worst, w), other + o
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return 0.0, [path]
        for i, (x, y) in enumerate(zip(a, b)):
            w, o = _rel_diff(x, y, f"{path}[{i}]")
            worst, other = max(worst, w), other + o
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if a != b:
            worst = abs(a - b) / max(abs(a), abs(b), 1e-300)
    elif a != b:
        other.append(path)
    return worst, other


def _rules(ev: dict) -> dict:
    """The decision rules as `closure criteria` reads them, in a few numbers."""
    def cell(v):
        return {"k": v["k"], "n": v["n"], "holds": v["holds"], "cp95_lower": v["cp95_lower"]}
    h4 = ev["H1.4"]
    return {"scope": ev["scope"], "H1.1": ev["H1.1"]["holds"], "threshold_method": ev["H1.1"]["threshold_methods"],
            "H1.2": {k: ev["H1.2"][k] for k in ("holds", "k", "n", "cp95_upper")},
            "H1.3_primary_5_percent": {cl: cell(v) for cl, v in ev["H1.3"]["primary"].items()},
            "H1.3_stretch_2_percent": {cl: cell(v) for cl, v in ev["H1.3"]["stretch"].items()},
            "H1.4": {"holds": h4["holds"], "basis": h4["basis"], "floor_time_bound_coverage": h4["coverage_nonslack"],
                     "hidden_blocks": (h4["time"] or {}).get("n"),
                     "reported_only": {"calibrated_time_bound_coverage": (h4["time"] or {}).get("coverage_nonslack"),
                                       "calibrated_energy_bound_coverage": h4["energy_coverage_nonslack"],
                                       "floor_energy_bound_coverage": h4["energy_coverage_floor_bound"]}},
            "closure_gap_fraction": ev["closure_gap_fraction"],
            "slack_inflated_gap_fraction": ev["slack_inflated_gap_fraction"], "outcome": ev["outcome"], "why": ev["why"]}


def _diagnostics(run: Path) -> dict:
    """What the raw data add to a link-analysis trial's signed results: where the threshold came from, and what load
    the GPU was under in the blocks the test got wrong. A diagnostic, post hoc: it describes and decides nothing."""
    cfg, ref, aud, sched = _load_run(run)
    cal = calibrate(ref, cfg)
    a = link.audit(cal, aud["X"], {"energy": aud["E"], "busy": aud["B"]}, cfg.alpha)
    L, R = cfg.L, len(cal.score)
    B = len(aud["E"]) // L
    cap = block_capacity_j(cfg.n_gpu, cfg.p_max_w, L, cfg.dt)
    hid = aud["hid"][: B * L].reshape(B, L).sum(1)
    hf, hs = hid / cap, aud["hs"][: B * L].reshape(B, L).sum(1)
    lev, rlev = aud["lev"][: B * L].reshape(B, L), ref["lev"][: R * L].reshape(R, L)
    kinds = np.array([("none" if s is None else s["kind"]) for s in sched[:B]])
    fracs = np.array([(0.0 if s is None else float(s["frac"])) for s in sched[:B]])
    ze, zb = a["z"]["energy"] / cal.energy.scale, a["z"]["busy"] / cal.busy.scale
    score, thr = a["score"], float(a["threshold"]["combined"])
    null, hidden = kinds == "none", (kinds != "none") & (kinds != "slack") & (hid > 0)
    full_a, full_r = np.isclose(lev, 1.0).mean(1), np.isclose(rlev, 1.0).mean(1)     # share of windows at level 1
    high_a = (lev >= 0.9 - 1e-9).mean(1)

    def block(b, extra=None):
        d = {"audit_block": int(b), "score": float(score[b]), "energy_score": float(ze[b]), "busy_score": float(zb[b]),
             "share_of_windows_at_level_1": float(full_a[b]), "share_of_windows_at_level_0.9_or_1": float(high_a[b])}
        d.update(extra or {})
        return d

    order = np.argsort(-cal.score)
    top_ref = [{"reference_block": int(i), "score": float(cal.score[i]),
                "energy_score": float(cal.energy.z[i] / cal.energy.scale),
                "busy_score": float(cal.busy.z[i] / cal.busy.scale),
                "share_of_windows_at_level_1": float(full_r[i])} for i in order[:5]]

    def side(mask_ref, mask_aud):
        mr, mn, mh = mask_ref, null & mask_aud, hidden & mask_aud
        big, small = mh & (hf >= 0.05 * (1 - 1e-6)), mh & (hf < 0.05 * (1 - 1e-6))
        return {"reference_blocks": int(mr.sum()),
                "reference_mean_score": float(cal.score[mr].mean()) if mr.any() else None,
                "reference_highest_score": float(cal.score[mr].max()) if mr.any() else None,
                "null_audit_blocks": int(mn.sum()), "false_alarms": int((score[mn] > thr).sum()),
                "null_audit_highest_score": float(score[mn].max()) if mn.any() else None,
                "hidden_blocks_at_5_percent_or_more": int(big.sum()), "missed_at_5_percent_or_more": int((score[big] <= thr).sum()),
                "hidden_blocks_under_5_percent": int(small.sum()), "missed_under_5_percent": int((score[small] <= thr).sum())}

    edges = np.logspace(-4, -0.5, 15)                                   # trial._pooled_f95's bins
    idx, det = np.digitize(hf[hidden], edges), (score > thr)[hidden]
    bins = [{"hidden_fraction_from": float(edges[b - 1]), "to": float(edges[b]), "detected": int(det[idx == b].sum()),
             "blocks": int((idx == b).sum())} for b in range(1, len(edges)) if (idx == b).any()]

    # a flat-out GPU: windows at requested level 1 with no hidden load, in the reference and the audit
    X = np.concatenate([ref["X"], aud["X"]])
    E, Bz = np.concatenate([ref["E"], aud["E"]]), np.concatenate([ref["B"], aud["B"]])
    t0 = np.concatenate([ref["t0"], aud["t0"]])
    m = np.isclose(np.concatenate([ref["lev"], aud["lev"]]), 1.0) & (np.concatenate([ref["hid"], aud["hid"]]) == 0)
    ups, watts, busy, hours = X[m, 1] / X[m, 0], E[m] / X[m, 0], Bz[m] / X[m, 0], (t0[m] - t0.min()) / 3600.0
    flat = {"windows": int(m.sum()), "watts_mean": float(watts.mean()), "busy_share_mean": float(busy.mean()),
            "units_per_s_percentiles_1_50_99": [float(q) for q in np.quantile(ups, [0.01, 0.5, 0.99])],
            "units_per_s_by_hour": [{"hour": int(h), "windows": int((hours.astype(int) == h).sum()),
                                     "units_per_s": float(ups[hours.astype(int) == h].mean())}
                                    for h in sorted(set(hours.astype(int).tolist()))]}
    wl = cfg.workload or {}
    clock = tier0.trial_clock(json.loads((run / "probe.json").read_text())) if (run / "probe.json").exists() else {}
    at = {c["mhz"]: c for c in clock.get("candidates", [])}
    locked = wl.get("locked_sm_mhz")
    return {"what": "diagnostic, post hoc: read off raw.npz after the run; it describes the run and decides nothing",
            "thresholds": {k: float(v) for k, v in a["threshold"].items()},
            "threshold_is": "the largest combined score among the reference blocks" if np.isclose(thr, cal.score.max())
                            else "a conformal quantile of the reference blocks' combined scores",
            "highest_reference_scores": top_ref,
            "false_alarms": [block(b) for b in np.where(null & (score > thr))[0]],
            "highest_null_audit_scores": [float(x) for x in np.sort(score[null])[::-1][:5]],
            "missed_hidden_blocks": [block(b, {"kind": str(kinds[b]), "label": float(fracs[b]),
                                               "hidden_fraction": float(hf[b]), "hidden_seconds": float(hs[b])})
                                     for b in np.where(hidden & (score <= thr))[0]],
            "gpu_flat_out_every_window_at_level_1": side(full_r == 1.0, full_a == 1.0),
            "every_other_block": side(full_r < 1.0, full_a < 1.0),
            "detection_by_hidden_fraction_bin": bins,
            "a_flat_out_gpu": flat,
            "trial_clock": {"locked_in_this_run_mhz": locked,
                            "estimated_flat_out_power_at_that_lock_w": (at.get(float(locked)) or {}).get("flat_out_power_w") if locked else None,
                            "power_limit_w": clock.get("power_limit_w"),
                            "amendment_v0_7_would_lock_mhz": clock.get("mhz"),
                            "estimated_flat_out_power_at_that_clock_w": (at.get(clock.get("mhz")) or {}).get("flat_out_power_w")}}


def reread_link(folder: Path) -> dict:
    """Runs from 0.8.0 on: the registered analysis is the link analysis. One or more bundles in the folder."""
    readme = (folder / "README.md").read_text(encoding="utf-8")
    out, trials = {"trials": {}}, []
    with tempfile.TemporaryDirectory() as tmp:
        for bundle in sorted(folder.glob("*tier0_bundle.tar.gz")):
            prefix = bundle.name[: -len("tier0_bundle.tar.gz")]                     # "", or "gpu0-" on Kaggle
            name = prefix.rstrip("-") or "run"
            sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
            assert sha in readme, f"{bundle.name}: its sha256 is not in {folder.name}/README.md"
            root = tier0.unpack(bundle, Path(tmp) / name, sha)
            run = next(root.glob("T1-*"))
            pre = json.loads((run / "prereg.json").read_text())
            signed = json.loads((run / "results.json").read_text())
            assert main(["verify", str(run)]) == 0
            again_path = Path(tmp) / f"{name}-again.json"
            assert main(["reanalyze", "--run", str(run), "--out", str(again_path)]) == 0
            again = json.loads(again_path.read_text())
            # results.json as signed, against the same analysis run here on raw.npz. Keys the analysis has gained since
            # (reported-only additions) are left out; the signed keys must all be reproduced.
            worst, other = _rel_diff(signed, {k: again[k] for k in signed if k in again})
            rep = physics.report(run)
            (folder / f"{prefix}physics.json").write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
            # the link-full analysis (amendment v0.7 (c)). A run that declared it as a comparison is read as one; for
            # runs 6 to 8, made before it existed, it is a POST HOC reading and the file it writes says so.
            declared = FULL in (pre["cfg"].get("comparisons") or ())
            full_path = run / f"results_{'comparison' if declared else 'posthoc'}_{FULL}.json"
            assert main(["reanalyze", "--run", str(run), "--analysis", FULL, "--out", str(full_path)]) == 0
            full = json.loads(full_path.read_text())
            out["trials"][name] = {
                "bundle": bundle.name, "bundle_sha256": sha, "trial": run.name, "code": pre["code"],
                "seed": pre["cfg"]["seed"], "campaign": pre["cfg"].get("campaign"),
                "registered_analysis": pre["cfg"]["analysis"], "verify": "passes",
                "registered_analysis_from_the_raw_data": {
                    "signed_keys_missing_here": sorted(k for k in signed if k not in again),
                    "values_that_are_not_numbers_and_differ": other,
                    "largest_relative_difference_in_any_number": worst,
                    "decision_rules": _rules(evaluate(again, pre["cfg"]["alpha"]))},
                "raw_data": _diagnostics(run),
                "link_full": {"reading": "declared comparison (amendment v0.7 (c)); decides nothing" if declared else
                              "POST HOC: this analysis was written after this run's data were seen; decides nothing",
                              "status": full["status"], "block_residual_sd": full["link"]["block_residual_sd"],
                              "block_residual_sd_registered": again["link"]["block_residual_sd"],
                              "threshold": full["link"]["thresholds"]["combined"],
                              "decision_rules": _rules(evaluate(full, pre["cfg"]["alpha"]))}}
            trials.append((pre, run, full_path.name))
        camps = {json.dumps(pre["cfg"].get("campaign"), sort_keys=True) for pre, _, _ in trials}
        first = trials[0][0]["cfg"].get("campaign")
        if first and len({(pre["cfg"]["campaign"] or {}).get("id") for pre, _, _ in trials}) == 1 and len(trials) == first["size"]:
            pooled_path = Path(tmp) / "pooled.json"
            in_order = [str(run) for _, run, _ in sorted(trials, key=lambda t: t[0]["cfg"]["campaign"]["index"])]
            assert main(["pool", "--runs", *in_order, "--out", str(pooled_path)]) == 0
            pooled = json.loads(pooled_path.read_text())
            full_pooled = Path(tmp) / "pooled-link-full.json"
            assert main(["pool", "--runs", *in_order, "--results", trials[0][2], "--out", str(full_pooled)]) == 0
            camp = {"id": first["id"], "trials": first["size"],
                    "decision_rules": _rules(evaluate(pooled, trials[0][0]["cfg"]["alpha"]))}
            back = folder / "pooled.json"
            if back.exists():                       # the pooled reading the session wrote, against the one made here
                theirs = json.loads(back.read_text())
                for d in (theirs, pooled):          # the trial folders' paths differ between the two machines
                    for t in d.get("pooling", {}).get("trials", []):
                        t.pop("run", None)
                worst, other = _rel_diff(theirs, pooled)
                camp["pooled_json_as_returned"] = {"values_that_are_not_numbers_and_differ": other,
                                                   "largest_relative_difference_in_any_number": worst}
            camp["link_full"] = {"reading": out["trials"][next(iter(out["trials"]))]["link_full"]["reading"],
                                 "decision_rules": _rules(evaluate(json.loads(full_pooled.read_text()), trials[0][0]["cfg"]["alpha"]))}
            out["campaign"] = camp
        else:
            assert camps == {"null"}, "a campaign with a trial missing is not read (closure pool refuses it too)"
    (folder / "reread.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def _registered_analysis(folder: Path) -> str:
    """'linear' or 'link': what the trial in the folder's first bundle pre-registered (0.7.0 did not record it)."""
    bundle = sorted(folder.glob("*tier0_bundle.tar.gz"))[0]
    with tempfile.TemporaryDirectory() as tmp:
        root = tier0.unpack(bundle, Path(tmp) / "peek")
        return json.loads((next(root.glob("T1-*")) / "prereg.json").read_text())["cfg"].get("analysis", "linear")


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["."]:
        folder = Path(arg).resolve()
        if _registered_analysis(folder) == "link":
            out = reread_link(folder)
            # the per-block lists are long: print the headline and leave the rest in reread.json
            print(json.dumps({"written": str(folder / "reread.json"),
                              "trials": {k: v["registered_analysis_from_the_raw_data"] for k, v in out["trials"].items()},
                              "campaign": out.get("campaign")}, indent=2))
        else:
            assert hashlib.sha256((folder / "tier0_bundle.tar.gz").read_bytes()).hexdigest() in (folder / "README.md").read_text()
            print(json.dumps(reread(folder), indent=2))
