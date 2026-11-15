"""The Tier 0 pilot on a Modal GPU (H100, H200, B200, B300 and others), started from your own computer.

Modal (modal.com) rents GPUs by the second, and every Starter workspace gets $30 of compute a month. On the rates its
pricing page gave on 14 November 2026 that covers one smoke pilot (about 2 h 20 min) on a B300 or a B200, two on an
H200 or an H100, or one medium pilot (about 5 h 40 min) on an H200 or an H100. `python scripts/modal_tier0.py
--estimate` prints the table without contacting Modal; nothing here runs before you start it, and nothing is sent
anywhere but your own Modal account.

What a run there is: NVML-only, inside Modal's gVisor sandbox, on a GPU nobody else is using. The kit has never run on
anything but a T4, so this would be the first run of its kind on that GPU. What it is not: the registered trial. There is
no independent meter, and clock and power-limit changes are not expected to be allowed in the sandbox: the probe then
drops those variants and says so, as on Kaggle, and the slack it reports is a lower bound. Anyone can run this in their
own account, which makes it an independent replication by someone other than the author.

Once:
    pip install modal          # on your computer, any OS
    modal setup                # signs you in through the browser and saves a token

From the repository folder:
    python scripts/modal_tier0.py --estimate                       # the cost of each GPU and profile; no Modal call
    modal run scripts/modal_tier0.py --rehearse                    # the pilot on a simulated GPU, in a CPU container
    modal run scripts/modal_tier0.py --gpu H100 --check            # a minute or two on the GPU: what doctor and preflight read
    modal run --detach scripts/modal_tier0.py --gpu H100           # the smoke pilot, about 2 h 20 min
    modal run --detach scripts/modal_tier0.py --gpu B200 --profile medium

Run --check first: it reads the GPU's NVML energy counter through Modal's sandbox, which the whole pilot needs, for a few
cents. `--detach` keeps the run going if this terminal closes. Every run is written to the Modal Volume
`plan-a-closure-runs` as it goes, and, if this terminal is still attached at the end, to runs/modal/<run>/ here. To fetch
a run later: `modal volume get plan-a-closure-runs <run> runs/modal/`. The volume also holds each trial's private
signing key (signing_key.bin): never send that file; send tier0_bundle.tar.gz, which leaves it out.

Modal may run a request for an H100 on an H200 at the H100 price (pass `H100!` to forbid that), and runs `B200+` on a B200
or a B300 at the B200 price; doctor.json in the bundle names the GPU that ran. Modal can also pre-empt a GPU container
and start the call again: each start gets its own attempt-<n> folder, so an interrupted attempt is kept, not overwritten.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REMOTE = "/root/plan-a-closure"             # where the repository sits in the container
MOUNT = "/runs"                             # where the Volume is mounted in the container
VOLUME = "plan-a-closure-runs"
APP = "plan-a-closure-tier0"

# Modal's published rates, in dollars per second (modal.com/pricing, read 14 November 2026). An estimate, not a bill.
RATES = {"T4": 0.000164, "L4": 0.000222, "A10": 0.000306, "L40S": 0.000542, "A100-40GB": 0.000583,
         "A100-80GB": 0.000694, "RTX-PRO-6000": 0.000842, "H100": 0.001097, "H200": 0.001261, "B200": 0.001736,
         "B300": 0.001972}
CPU_PER_CORE_S, MEM_PER_GIB_S = 0.0000131, 0.00000222
FREE_PER_MONTH = 30.0
CPU_CORES, MEM_MIB = 4.0, 32 * 1024          # the run's container: the load generator needs little CPU
ALIASES = {"H100!": "H100", "B200+": "B200", "A100": "A100-40GB"}   # billed as the GPU on the right
HOURS = {"smoke": 2 + 20 / 60, "medium": 5 + 40 / 60, "long": 11.0}  # docs/OPERATOR_TIER0.md (amendment v0.8)
TIMEOUT_H = {"smoke": 4, "medium": 8, "long": 15}                   # Modal allows up to 24 h
CHECK_TIMEOUT_S, REHEARSE_TIMEOUT_S = 20 * 60, 30 * 60
IGNORE = [".venv", ".venv-*", "runs", "**/__pycache__", "**/*.pyc", "**/*.egg-info", "**/.pytest_cache",
          "**/node_modules", "signing_key.bin", "**/signing_key.bin"]
# What comes back to this computer: never the private key, never raw.npz (it is inside the bundle).
DELIVERABLES = ("SUMMARY.md", "tier0_bundle.tar.gz", "doctor.md", "doctor.json", "mock-run/drill.json")


def canonical_gpu(name: str) -> str:
    """Modal's GPU type string for what the user typed (case-insensitive), or ValueError naming the choices."""
    known = {k.lower(): k for k in list(RATES) + list(ALIASES)}
    key = (name or "").strip().lower()
    if key not in known:
        raise ValueError(f"unknown GPU '{name}': one of {', '.join(sorted(known.values()))}")
    return known[key]


def billed_as(gpu: str) -> str:
    return ALIASES.get(gpu, gpu)


def dollars_per_hour(gpu: str) -> float:
    return 3600 * (RATES[billed_as(gpu)] + CPU_CORES * CPU_PER_CORE_S + MEM_MIB / 1024 * MEM_PER_GIB_S)


def estimate(gpu: str, profile: str) -> float:
    """Dollars for one pilot of this profile on this GPU, at the published rates, container CPU and memory included."""
    return HOURS[profile] * dollars_per_hour(gpu)


def cost_table() -> str:
    L = [f"Estimated cost of one pilot at Modal's published rates (read 14 November 2026), with {CPU_CORES:g} CPU cores "
         f"and {MEM_MIB // 1024} GiB; the Starter plan includes ${FREE_PER_MONTH:.0f} a month.", "",
         "| GPU | $/hour | smoke (2 h 20 min) | medium (5 h 40 min) | long (11 h) | smoke runs in $30 |",
         "| --- | --- | --- | --- | --- | --- |"]
    for g in sorted(RATES, key=lambda k: RATES[k], reverse=True):
        L.append(f"| {g} | {dollars_per_hour(g):.2f} | {estimate(g, 'smoke'):.2f} | {estimate(g, 'medium'):.2f} | "
                 f"{estimate(g, 'long'):.2f} | {int(FREE_PER_MONTH // estimate(g, 'smoke'))} |")
    L += ["", "`--check` uses about two minutes of the GPU; `--rehearse` uses no GPU. Rates change: modal.com/pricing."]
    return "\n".join(L)


def parse(argv) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="modal run scripts/modal_tier0.py",
                                 description="the plan-a-closure Tier 0 pilot on a Modal GPU")
    ap.add_argument("--gpu", default="H100", help="Modal GPU type: H100, H100!, H200, B200, B200+, B300, RTX-PRO-6000, "
                    "A100-80GB, A100-40GB, L40S, L4, A10, T4 (default H100)")
    ap.add_argument("--profile", choices=list(HOURS), default="smoke",
                    help="smoke (about 2 h 20 min, checks the pipeline), medium (about 5 h 40 min) or long (about 11 h); "
                         "medium and long can read the pre-registered rules H1.1 to H1.4")
    what = ap.add_mutually_exclusive_group()
    what.add_argument("--check", action="store_true", help="only closure doctor and preflight on the GPU (a minute or two)")
    what.add_argument("--rehearse", action="store_true", help="the whole pilot on a simulated GPU, in a CPU container")
    what.add_argument("--estimate", action="store_true", help="print what each GPU and profile costs, and stop")
    ap.add_argument("--skip-tests", action="store_true", help="leave out the unit tests at the start of the pilot")
    ap.add_argument("--mock-run", action="store_true", help="after the pilot, A Narrow Path's mock training run (minutes)")
    ap.add_argument("--name", default=None, help="the run's folder name (default: mode, GPU, profile and UTC time)")
    a = ap.parse_args(list(argv))
    try:
        a.gpu = canonical_gpu(a.gpu)
    except ValueError as e:
        ap.error(str(e))
    a.mode = "estimate" if a.estimate else "rehearse" if a.rehearse else "check" if a.check else "pilot"
    if a.name is None:
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        slug = a.gpu.lower().replace("!", "-pinned").replace("+", "-plus")
        a.name = {"rehearse": f"rehearse-{stamp}", "check": f"check-{slug}-{stamp}"}.get(a.mode,
                                                                                         f"{slug}-{a.profile}-{stamp}")
    elif not all(c.isalnum() or c in "-_." for c in a.name) or a.name.startswith("."):
        ap.error("--name takes letters, digits, '-', '_' and '.' only")
    return a


def remote_commands(mode: str, out: str, profile: str = "smoke", skip_tests: bool = False, mock_run: bool = False) -> list:
    """The commands the container runs, from the repository folder, writing under `out` (a new folder)."""
    if mode == "check":
        return [["python3", "-m", "closure.cli", "doctor", "--out", out],
                ["python3", "-m", "closure.cli", "preflight", "--gpu", "0"]]
    if mode == "rehearse":
        return [["bash", "scripts/run_anywhere.sh", "--no-venv", "--skip-tests", "--out", out]]
    if mode == "pilot":
        return [["bash", "scripts/run_anywhere.sh", "--hardware", "--no-venv", "--profile", profile, "--out", out]
                + (["--skip-tests"] if skip_tests else []) + (["--mock-run"] if mock_run else [])]
    raise ValueError(f"unknown mode {mode!r}")


def next_attempt(base: pathlib.Path) -> pathlib.Path:
    """base/attempt-<n> for the first n not taken: a call Modal restarts after pre-emption writes beside the old one."""
    n = 1
    while (base / f"attempt-{n}").exists():
        n += 1
    return base / f"attempt-{n}"


def execute(mode: str, run: str, profile: str, skip_tests: bool, mock_run: bool, requested_gpu: str,
            root: str = REMOTE, mount: str = MOUNT, commit=None) -> dict:
    """What the container does: run the commands, keep a console log beside them, and return the deliverables."""
    attempt = next_attempt(pathlib.Path(mount) / run)
    attempt.mkdir(parents=True)
    out = attempt / mode
    started = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    (attempt / "launcher.txt").write_text(
        f"scripts/modal_tier0.py\nmode: {mode}\nGPU requested: {requested_gpu}\nprofile: {profile}\nskip tests: "
        f"{skip_tests}\nmock run: {mock_run}\nstarted (UTC): {started}\nattempt: {attempt.name}\n", encoding="utf-8")
    log = attempt / "console.log"
    rc = 0
    try:
        with open(log, "w", encoding="utf-8") as fh:
            for cmd in remote_commands(mode, str(out), profile, skip_tests, mock_run):
                fh.write("$ " + " ".join(cmd) + "\n")
                fh.flush()
                p = subprocess.Popen(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     errors="replace")
                for line in p.stdout:                  # shown in `modal run` and kept
                    print(line, end="", flush=True)
                    fh.write(line)
                rc = p.wait() or rc
                fh.write(f"[exit {p.returncode}]\n")
                if mode != "check" and p.returncode != 0:
                    break
    finally:
        if commit is not None:
            commit()
    files = {}
    for rel in DELIVERABLES:
        f = out / rel
        if f.is_file():
            files[rel] = f.read_bytes()
    files["console.log"] = log.read_bytes()
    files["launcher.txt"] = (attempt / "launcher.txt").read_bytes()
    return {"run": run, "attempt": attempt.name, "exit": int(rc), "files": files}


def save_locally(res: dict, dest_root: pathlib.Path = ROOT / "runs" / "modal") -> pathlib.Path:
    dest = dest_root / res["run"] / res["attempt"]
    for rel, data in res["files"].items():
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return dest


def report(a: argparse.Namespace, res: dict, dest: pathlib.Path) -> str:
    L = ["", f"== {a.mode} on {a.gpu}" + (f", {a.profile} trial" if a.mode == "pilot" else "")
         + f": exit {res['exit']} ({res['run']}/{res['attempt']})", f"saved here:   {dest}",
         f"and in Modal: modal volume get {VOLUME} {res['run']} runs/modal/"]
    bundle = res["files"].get("tier0_bundle.tar.gz")
    if bundle:
        L.append(f"bundle:       {dest / 'tier0_bundle.tar.gz'}  sha256 {hashlib.sha256(bundle).hexdigest()}")
    if a.mode == "check":
        L += ["", "Read doctor.md and console.log above: if the energy counter reads 'yes' and preflight shows no FAIL,",
              f"the pilot can run here:  modal run --detach scripts/modal_tier0.py --gpu {a.gpu}"]
    elif a.mode == "pilot" and bundle:
        L += ["", "To add it to the public record, open an issue at https://github.com/AnonRish/plan-a-closure/issues",
              "and attach tier0_bundle.tar.gz (it leaves out the private signing key). Every run is published whatever",
              "it shows. Do not send signing_key.bin, which stays in the Modal Volume."]
    return "\n".join(L)


try:
    import modal
except ModuleNotFoundError:                 # --help and the tests work without Modal; `modal run` needs it
    modal = None

if modal is not None:
    image = (modal.Image.debian_slim(python_version="3.12")
             .apt_install("git")
             .pip_install("torch", "nvidia-ml-py>=12", "opentimestamps-client")
             .add_local_dir(ROOT, REMOTE, copy=True, ignore=IGNORE)            # a Path, so a Windows checkout works too
             .run_commands(f"python3 -m pip install -e '{REMOTE}[test,hw]'")
             .env({"PYTHONUNBUFFERED": "1"}))
    app = modal.App(APP)
    runs_volume = modal.Volume.from_name(VOLUME, create_if_missing=True)

    @app.function(image=image, gpu="H100", timeout=TIMEOUT_H["smoke"] * 3600, cpu=CPU_CORES, memory=MEM_MIB,
                  volumes={MOUNT: runs_volume})
    def on_gpu(mode: str, run: str, profile: str, skip_tests: bool, mock_run: bool, requested_gpu: str) -> dict:
        return execute(mode, run, profile, skip_tests, mock_run, requested_gpu, commit=runs_volume.commit)

    @app.function(image=image, timeout=REHEARSE_TIMEOUT_S, cpu=CPU_CORES, memory=MEM_MIB, volumes={MOUNT: runs_volume})
    def on_cpu(run: str) -> dict:
        return execute("rehearse", run, "smoke", True, False, "none (simulated GPU)", commit=runs_volume.commit)

    @app.local_entrypoint()
    def main(*argv):
        rc = local(argv)
        if rc:
            raise SystemExit(rc)


def local(argv, gpu_fn=None, cpu_fn=None, dest_root: pathlib.Path = None, echo=print) -> int:
    """The part that runs on your computer: parse, estimate, start the run in Modal, save what comes back."""
    a = parse(argv)
    if a.mode == "estimate":
        echo(cost_table())
        return 0
    gpu_fn = gpu_fn if gpu_fn is not None else globals().get("on_gpu")
    cpu_fn = cpu_fn if cpu_fn is not None else globals().get("on_cpu")
    if gpu_fn is None or cpu_fn is None:
        echo("Modal is not installed here: pip install modal && modal setup, then use `modal run scripts/modal_tier0.py`")
        return 2
    if a.mode == "rehearse":
        echo(f"rehearsal on a simulated GPU in a CPU container (no physical claim) -> {VOLUME}/{a.name}")
        res = cpu_fn.remote(a.name)
    else:
        if a.mode == "check":
            echo(f"{a.gpu}: doctor and preflight only, about two minutes (about ${dollars_per_hour(a.gpu) / 30:.2f})")
            timeout = CHECK_TIMEOUT_S
        else:
            echo(f"{a.gpu}, {a.profile} trial: about {HOURS[a.profile]:.1f} h, about ${estimate(a.gpu, a.profile):.2f} at "
                 f"Modal's published rates (billed as {billed_as(a.gpu)}); the Starter plan includes "
                 f"${FREE_PER_MONTH:.0f} a month")
            timeout = TIMEOUT_H[a.profile] * 3600
        if not hasattr(gpu_fn, "with_options"):
            echo("this Modal client is too old to choose the GPU at run time: pip install -U modal")
            return 2
        res = gpu_fn.with_options(gpu=a.gpu, timeout=int(timeout)).remote(a.mode, a.name, a.profile, a.skip_tests,
                                                                           a.mock_run, a.gpu)
    dest = save_locally(res, dest_root if dest_root is not None else ROOT / "runs" / "modal")
    echo(report(a, res, dest))
    return int(res["exit"])


if __name__ == "__main__":                  # plain `python scripts/modal_tier0.py --estimate` works without Modal
    sys.exit(local(sys.argv[1:]))
