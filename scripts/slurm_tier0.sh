#!/usr/bin/env bash
#SBATCH --job-name=plan-a-closure-tier0
#SBATCH --gpus=h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=0-04:00
#SBATCH --output=plan-a-closure-tier0-%j.out
#
# The Tier 0 pilot as a Slurm batch job on one whole H100, for a university or national research cluster. Many such
# services are free to researchers and, through a sponsoring faculty member, to their students. The GPU type name in
# --gpus and the limits above are your cluster's own: change them to what its documentation gives.
#
#   1. Once, on a login node (it has internet; compute nodes may not):
#        bash scripts/slurm_tier0.sh --setup
#   2. Submit from the repository folder (the job runs in the folder it was submitted from):
#        sbatch --account=<account> scripts/slurm_tier0.sh                                     smoke, about 2 h 20 min
#        sbatch --account=<account> --time=0-08:00 scripts/slurm_tier0.sh --profile medium     about 5 h 40 min
#        sbatch --account=<account> --time=0-15:00 scripts/slurm_tier0.sh --profile long       about 11 h
#   3. When it ends: runs/slurm-<job id>/SUMMARY.md and runs/slurm-<job id>/tier0_bundle.tar.gz (the file to send back;
#      it leaves out the trial's private signing key).
#
# Options: --setup, --profile smoke|medium|long, --skip-tests, --mock-run, --dry-run (print what would run, run nothing).
#
# What this run is: the GPU's own NVML counters on a bare-metal node, no independent meter, so a shakedown like the T4
# runs, and the first on an H100. `--gpus=h100:1` asks for a whole GPU: clusters often split some GPUs into MIG slices,
# and the energy counter covers the whole GPU, so the pilot refuses a slice (closure doctor says why). A batch
# job has no root, so the probe cannot lock clocks or set power limits: those variants are dropped and noted, and the
# slack it reports is a lower bound. Slurm's time limit sends SIGTERM; the pilot then restores the GPU and still writes
# its summary and bundle. The job checks before it starts that its time limit covers the profile.

set -u
MODE=job; PROFILE=smoke; SKIP=""; MOCKRUN=0; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --setup) MODE=setup ;;
    --profile) [ $# -ge 2 ] || { echo "--profile needs smoke, medium or long" >&2; exit 2; }; PROFILE="$2"; shift ;;
    --skip-tests) SKIP="--skip-tests" ;;
    --mock-run) MOCKRUN=1 ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '9,29p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done
case "$PROFILE" in smoke) NEED_MIN=140 ;; medium) NEED_MIN=340 ;; long) NEED_MIN=660 ;;
  *) echo "--profile is smoke, medium or long (got '$PROFILE')" >&2; exit 2 ;; esac

die() { printf '\nstopped: %s\n' "$*" >&2; exit 1; }
run() { if [ "$DRY" = 1 ]; then printf '+ %s\n' "$*"; else "$@"; fi; }

# sbatch runs a copy of this script from Slurm's spool directory, so the repository is where the job was submitted from.
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then cd "$SLURM_SUBMIT_DIR" || die "cannot enter $SLURM_SUBMIT_DIR"
else cd "$(dirname "${BASH_SOURCE[0]}")/.." || die "cannot find the repository"; fi
[ -f pyproject.toml ] && [ -d src/closure ] || die "$PWD is not a plan-a-closure checkout: submit with sbatch from the repository folder"
VENV="${CLOSURE_VENV:-$PWD/.venv-slurm}"
PY="$VENV/bin/python"

load_python() {   # the cluster's Python module, when there is one (Lmod and Environment Modules define `module`)
  if command -v module >/dev/null 2>&1 || type module >/dev/null 2>&1; then
    module load python/3.12 >/dev/null 2>&1 || module load python >/dev/null 2>&1 || true
  fi
}

# Minutes left in this job, from squeue's %L ([days-]hours:minutes:seconds, or minutes:seconds); empty if unknown.
minutes_left() {
  [ -n "${SLURM_JOB_ID:-}" ] && command -v squeue >/dev/null 2>&1 || return 0
  local L; L="$(squeue -h -j "$SLURM_JOB_ID" -o %L 2>/dev/null | head -n 1 | tr -d ' ')"
  case "$L" in ""|UNLIMITED|INVALID|NOT_SET) return 0 ;; esac
  local d=0 h=0 m=0 rest="$L"
  case "$rest" in *-*) d="${rest%%-*}"; rest="${rest#*-}" ;; esac
  local n; n="$(printf '%s' "$rest" | tr -cd ':' | wc -c | tr -d ' ')"
  if [ "$n" = 2 ]; then h="${rest%%:*}"; rest="${rest#*:}"; m="${rest%%:*}"
  elif [ "$n" = 1 ]; then m="${rest%%:*}"
  else return 0; fi
  echo $(( 10#$d * 1440 + 10#$h * 60 + 10#$m ))
}

if [ "$MODE" = setup ]; then
  load_python
  command -v python3 >/dev/null 2>&1 || die "no python3 here: load your cluster's Python module (module load python)"
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || die "Python 3.10 or newer is needed"
  run python3 -m venv "$VENV" || die "could not create $VENV"
  run "$PY" -m pip install -q --upgrade pip
  run "$PY" -m pip install -q -e ".[test,hw]" "nvidia-ml-py>=12" opentimestamps-client || die "pip install failed (see above)"
  run "$PY" -m closure.cli doctor || true      # on a login node there is no GPU; this only shows the install works
  echo
  echo "ready. Submit from $PWD:  sbatch --account=<account> scripts/slurm_tier0.sh"
  exit 0
fi

# ---- the batch job ----------------------------------------------------------------------------------------------------
[ "$DRY" = 1 ] || [ -x "$PY" ] || die "no $VENV: run 'bash scripts/slurm_tier0.sh --setup' on a login node first"
LEFT="$(minutes_left)"
if [ -n "$LEFT" ] && [ "$LEFT" -lt "$NEED_MIN" ]; then
  die "this job has $LEFT minutes left and the $PROFILE pilot needs about $NEED_MIN: resubmit with a longer --time (smoke 0-04:00, medium 0-08:00, long 0-15:00)"
fi
load_python
OUT="runs/slurm-${SLURM_JOB_ID:-$(date -u +%Y%m%d-%H%M%S)}"
[ -e "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ] && die "$OUT is not empty"
echo "== node ${SLURMD_NODENAME:-$(hostname)}, job ${SLURM_JOB_ID:-none}, CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}, $PROFILE trial -> $OUT"
command -v nvidia-smi >/dev/null 2>&1 && run nvidia-smi -L
export PYTHONUNBUFFERED=1
# shellcheck disable=SC2086
run "$PY" -m closure.cli tier0 --confirm-hardware --gpu 0 --trial-profile "$PROFILE" $SKIP --out "$OUT"; RC=$?
if [ "$MOCKRUN" = 1 ] && { [ "$DRY" = 1 ] || [ -f "$OUT/probe.json" ]; }; then
  run "$PY" -m closure.cli treaty mock-run --device cuda:0 --probe "$OUT/probe.json" --budget-flop 1e16 --dim 4096 \
    --layers 8 --batch 2048 --out "$OUT/mock-run" || echo "note: the mock training run did not finish; the pilot's result is unaffected"
fi
if [ -f "$OUT/tier0_bundle.tar.gz" ]; then
  echo
  echo "summary: $OUT/SUMMARY.md"
  echo "bundle:  $OUT/tier0_bundle.tar.gz  sha256 $("$PY" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$OUT/tier0_bundle.tar.gz")"
  echo "send the bundle (never signing_key.bin): https://github.com/AnonRish/plan-a-closure/issues"
fi
exit "$RC"
