"""The hardware runs on record as one table, re-derived from the bundles in this folder.

    python results/record.py              # print the table
    python results/record.py --write      # rewrite results/README.md (tests/test_runs_on_record.py checks it is current)

Only the first two columns are typed in by hand. Everything else is read from each bundle as it came back: its
SHA-256, whether `closure verify` passes (hash chain, signature, commitments), the code that ran, and the
pre-registered decision rules read off the signed results, exactly as `closure criteria` reads them. A campaign's row
is `closure pool` on its trials. Continuous integration runs this on every push and shows the table on the run's page.
"""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

from closure import tier0
from closure.cli import main, verify_checks, _verified
from closure.criteria import evaluate

HERE = Path(__file__).resolve().parent

# (run, when and where, folder, bundle file, trial folder inside the bundle; None where no trial was reached)
RUNS = [
    ("1", "8 Nov 2026, Colab VM", "shakedown-2026-11-08-colab-t4", "tier0_bundle.tar.gz", None),
    ("2", "8 Nov 2026, Colab VM", None, None, None),
    ("3", "8 Nov 2026, Colab VM", "shakedown-2026-11-08-colab-t4-run3", "tier0_bundle.tar.gz", "T1-smoke"),
    ("4", "8 to 9 Nov 2026, Colab VM", "shakedown-2026-11-08-colab-t4-run4", "tier0_bundle.tar.gz", "T1-smoke"),
    ("5", "8 to 9 Nov 2026, Kaggle container", "shakedown-2026-11-08-kaggle-t4-run5", "tier0_bundle.tar.gz", "T1-long"),
    ("6", "11 to 12 Nov 2026, Kaggle container, GPU 0", "shakedown-2026-11-11-kaggle-t4-runs6-7", "gpu0-tier0_bundle.tar.gz", "T1-long"),
    ("7", "11 to 12 Nov 2026, Kaggle container, GPU 1", "shakedown-2026-11-11-kaggle-t4-runs6-7", "gpu1-tier0_bundle.tar.gz", "T1-long"),
    ("8", "12 Nov 2026, Colab VM", "shakedown-2026-11-12-colab-t4-run8", "tier0_bundle.tar.gz", "T1-medium"),
]
CAMPAIGNS = [("6 + 7", "the campaign the two were declared as, read whole", ("6", "7"))]
NOTES = {"1": "stopped at `hw-selftest`, before any trial (a unit of work sized for an H100)",
         "2": "the bundle was lost when the session ended; nothing to re-read (docs/DEVIATIONS.md section 2)"}
HEAD = ("| run | when and where | code | trial | bundle sha256 | verify | H1.1 | H1.2 false alarms | H1.3 at 5% or more "
        "| H1.3 at 2% or more | H1.4 | closure gap; with slack | outcome |")


def _quiet(argv) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return main(argv)


def _word(h) -> str:
    return "n/a" if h is None else "holds" if h else "**fails**"


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _detection(level) -> str:
    if not level:
        return "n/a"
    pooled = level.get("pooled_nonslack") or {}
    decided = [v["holds"] for c, v in level.items() if c != "pooled_nonslack" and v["holds"] is not None]
    verdict = "not decided" if not decided else "holds" if all(decided) else "**fails**"
    return f"{verdict}: {pooled.get('k')}/{pooled.get('n')}"


def _cells(res: dict, alpha: float) -> list:
    ev = evaluate(res, alpha)
    h2, h4 = ev["H1.2"], ev["H1.4"]
    h13 = ev["H1.3"] or {}
    n4 = (h4.get("time") or {}).get("n")
    return [_word(ev["H1.1"]["holds"]),
            ("not decided" if h2["holds"] is None else _word(h2["holds"])) + f": {h2['k']}/{h2['n']}",
            _detection(h13.get("primary")), _detection(h13.get("stretch")),
            _word(h4["holds"]) + (f": {_pct(h4['coverage_nonslack'])}" + (f" of {n4}" if n4 else "") + f" ({h4['basis']} bound)"
                                 if h4["holds"] is not None else ""),
            f"{_pct(ev['closure_gap_fraction'])}; {_pct(ev['slack_inflated_gap_fraction'])}",
            f"**{ev['outcome']}**"]


def rows(results: Path = HERE) -> list:
    out, trials = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        for run, where, folder, tgz, trial in RUNS:
            if folder is None:
                out.append(f"| {run} | {where} | | | | | | | | | | | {NOTES[run]} |")
                continue
            path = results / folder / tgz
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if sha not in (results / folder / "README.md").read_text(encoding="utf-8"):
                raise SystemExit(f"{path}: its sha256 {sha} is not in {folder}/README.md")
            root = tier0.unpack(path, Path(tmp) / f"run{run}", sha)
            link = f"[`{sha[:16]}`]({folder}/)"
            if trial is None or not (root / trial / "results.json").exists():
                out.append(f"| {run} | {where} | | | {link} | | | | | | | | {NOTES.get(run, 'no trial results in the bundle')} |")
                continue
            pre = json.loads((root / trial / "prereg.json").read_text())
            res = json.loads((root / trial / "results.json").read_text())
            code = pre.get("code") or {}
            ok = _verified(verify_checks(root / trial))
            trials[run] = (root / trial, pre)
            cfg = pre["cfg"]
            out.append("| " + " | ".join(
                [run, where, f"{code.get('package', '?')} `{str(code.get('git_commit') or '')[:7]}`",
                 f"{trial[3:]}, {res.get('analysis', 'linear')}", link, "passes" if ok else "**FAILS**"]
                + _cells(res, float(cfg.get("alpha", 0.01)))) + " |")
        for label, what, members in CAMPAIGNS:
            pooled = Path(tmp) / f"pooled-{'-'.join(members)}.json"
            if _quiet(["pool", "--runs", *[str(trials[m][0]) for m in members], "--out", str(pooled)]) != 0:
                raise SystemExit(f"closure pool refused campaign {label}")
            pre = trials[members[0]][1]
            out.append("| " + " | ".join(
                [f"**{label}**", what, "", f"{(pre['cfg'].get('campaign') or {}).get('id', '')}", "", "each passes"]
                + _cells(json.loads(pooled.read_text()), float(pre["cfg"].get("alpha", 0.01)))) + " |")
    return out


def page(results: Path = HERE) -> str:
    return "\n".join([
        "# The hardware runs on record", "",
        "Every run of this kit on a real GPU, whatever it showed. This page is written by `python results/record.py "
        "--write` from the bundles in this folder, and a test fails if it is out of date: apart from the first two "
        "columns, nothing in the table is typed in by hand. The account of each run, with what failed and why, is "
        "[docs/DEVIATIONS.md](../docs/DEVIATIONS.md).", "",
        "All eight are shakedowns on Tesla T4s in cloud sessions, with the GPU's own NVML counters as the only meter. "
        "A T4 is not the target device and NVML can be spoofed by whoever runs the machine, so none of this is a "
        "claim about Plan A: it is what the pipeline and the pre-registered analysis did on the hardware that was "
        "available. The registered trial needs H100-class GPUs and an independent power meter "
        "([docs/PREREGISTRATION.md](../docs/PREREGISTRATION.md)).", "",
        HEAD, "| " + " | ".join(["---"] * 13) + " |", *rows(results), "",
        "Reading the columns. **H1.1**: the detection threshold is valid (conformal, since amendment v0.6). **H1.2**: "
        "false alarms on blocks with no hidden load, at most 3% of at least 200. **H1.3**: hidden loads of at least "
        "5% (primary) and 2% (stretch) of the GPU's capacity are detected at least 95% of the time in every class "
        "that has 8 or more such blocks; the count is over all classes. **H1.4**: the bound covers what the hidden "
        "load really used in at least 95% of hidden blocks. **Closure gap**: the smallest hidden share of capacity "
        "from which detection stays at 95% or more; **with slack** adds the efficiency slack the probe measured on "
        "that GPU, and the outcome needs that sum at 5% or less. Runs 3 to 5 used the straight-line analysis that "
        "run 5 showed to be wrong for a power-limited GPU; runs 6 to 8 are the first prospective tests of its "
        "replacement.", "",
        "To check a row yourself: `closure verify` and `closure criteria --run` on the unpacked bundle, or "
        "`python results/reread.py results/<folder>` for everything the documents quote. "
        "[docs/VERIFY_IT_YOURSELF.md](../docs/VERIFY_IT_YOURSELF.md) has the commands.", "",
        "Which settings the slack comes from, and how much of it each rule a regime could adopt (fixed clocks, a "
        "pinned software stack, energy predicted from the data) would remove, read from the same bundles: "
        "[SLACK_LEFT.md](SLACK_LEFT.md). It is descriptive and decides nothing.", ""])


if __name__ == "__main__":
    text = page()
    if "--write" in sys.argv[1:]:
        (HERE / "README.md").write_text(text, encoding="utf-8")
        print(f"wrote {HERE / 'README.md'}")
    else:
        print(text)
