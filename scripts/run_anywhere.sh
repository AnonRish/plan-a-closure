#!/usr/bin/env bash
# One command from a fresh clone to a result, on any machine. Run it from the repository:
#
#   git clone https://github.com/AnonRish/plan-a-closure && cd plan-a-closure
#   bash scripts/run_anywhere.sh               look at this machine, then run the whole pilot on a simulated GPU
#                                              (about 3 minutes with the install; needs no GPU)
#   bash scripts/run_anywhere.sh --check       only look: which pilot steps would run on each GPU here, and why
#   bash scripts/run_anywhere.sh --hardware    the pilot on a real NVIDIA GPU (about 2 h 20 min of exclusive use)
#
# Options for --hardware:
#   --gpu N         which GPU, counted as CUDA counts them (default 0)
#   --profile P     smoke (default: 2 h 20 min, checks the pipeline), medium (about 5 h 40 min) or long (about 11 h);
#                   medium and long are large enough to read the pre-registered rules H1.1 to H1.4
#   --no-sudo       never use sudo. Without root the clock and power-limit variants are dropped and noted
#   --stamp         also install the OpenTimestamps client, so the pre-registration is timestamped on public calendars
#                   before any trial data exist. This is the only network use after installation
#   --mock-run      after the pilot, A Narrow Path's mock training run on the same GPU (a few minutes)
# Options for every mode:
#   --out DIR       where the run goes (default runs/<mode>-<UTC time>); a new or empty folder
#   --no-venv       install into the Python environment already active instead of ./.venv (inside a container or a
#                   notebook image that ships its own PyTorch)
#   --python EXE    the Python to use (default python3; 3.10 or newer)
#   --skip-tests    leave out the unit tests at the start of the pilot
#
# Nothing is sent anywhere. A run leaves a folder and one file to send back, tier0_bundle.tar.gz, which leaves out the
# run's private signing key. docs/VERIFY_IT_YOURSELF.md says what each mode shows and what none of them can show.

set -u
MODE=mock; GPU=0; PROFILE=smoke; OUT=""; VENV=1; PY="${PYTHON:-python3}"; SUDO=auto; STAMP=0; MOCKRUN=0; SKIP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE=check ;;
    --mock) MODE=mock ;;
    --hardware) MODE=hardware ;;
    --gpu) [ $# -ge 2 ] || { echo "--gpu needs a number" >&2; exit 2; }; GPU="$2"; shift ;;
    --profile) [ $# -ge 2 ] || { echo "--profile needs smoke, medium or long" >&2; exit 2; }; PROFILE="$2"; shift ;;
    --out) [ $# -ge 2 ] || { echo "--out needs a folder" >&2; exit 2; }; OUT="$2"; shift ;;
    --python) [ $# -ge 2 ] || { echo "--python needs an executable" >&2; exit 2; }; PY="$2"; shift ;;
    --no-venv) VENV=0 ;;
    --no-sudo) SUDO=never ;;
    --stamp) STAMP=1 ;;
    --mock-run) MOCKRUN=1 ;;
    --skip-tests) SKIP=1 ;;
    -h|--help) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done
case "$GPU" in ''|*[!0-9]*) echo "--gpu needs a number, counted as CUDA counts GPUs (got '$GPU')" >&2; exit 2 ;; esac
case "$PROFILE" in smoke|medium|long) ;; *) echo "--profile is smoke, medium or long (got '$PROFILE')" >&2; exit 2 ;; esac

say() { printf '\n== %s\n' "$*"; }
die() { printf '\nstopped: %s\n' "$*" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || die "cannot find the repository this script is in"
cd "$ROOT" || die "cannot enter $ROOT"
[ -f pyproject.toml ] && [ -d src/closure ] || die "$ROOT is not a plan-a-closure checkout"

command -v "$PY" >/dev/null 2>&1 || die "'$PY' not found: install Python 3.10 or newer, or name one with --python"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || die "$("$PY" -V 2>&1) is too old: plan-a-closure needs Python 3.10 or newer (name another with --python)"

if [ "$VENV" = 1 ]; then
  if [ ! -x .venv/bin/python ]; then
    say "creating ./.venv"
    "$PY" -m venv .venv || die "could not create a virtual environment (on Debian or Ubuntu: apt install python3-venv), or use --no-venv"
  fi
  PYBIN="$ROOT/.venv/bin/python"
else
  PYBIN="$(command -v "$PY")"
fi

# The simulated pilot and the look at the machine need numpy, cryptography and pytest, plus NVIDIA's small NVML binding
# to read a GPU if there is one. Only a hardware run needs PyTorch (a download of about 3 GB when it is not there yet).
if [ "$MODE" = hardware ]; then EXTRAS="test,hw"; else EXTRAS="test"; fi
say "installing plan-a-closure[$EXTRAS] into $("$PYBIN" -c 'import sys; print(sys.prefix)')"
"$PYBIN" -m pip install -q --disable-pip-version-check -e ".[$EXTRAS]" "nvidia-ml-py>=12" \
  || die "pip install failed (see above). With --no-venv on a system Python, drop --no-venv so that the install goes into ./.venv"
if [ "$STAMP" = 1 ]; then
  "$PYBIN" -m pip install -q --disable-pip-version-check opentimestamps-client \
    || echo "note: the OpenTimestamps client did not install; the pre-registration's hash is still in the signed chain"
  PATH="$(dirname "$PYBIN"):$PATH"; export PATH          # so that the run finds `ots`
fi
closure() { "$PYBIN" -m closure.cli "$@"; }
sha256_of() { "$PYBIN" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"; }

say "this machine (closure doctor: reads it, runs nothing on the GPU)"
closure doctor || die "closure doctor failed, which it should not on any machine: please report the lines above"
[ "$MODE" = check ] && exit 0

STAMP_NOW="$(date -u +%Y%m%d-%H%M%S)"
[ -n "$OUT" ] || OUT="runs/$MODE-$STAMP_NOW"
if [ -e "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then
  die "$OUT is not empty: choose a new --out, so that no earlier run is mixed into this one"
fi
SKIPARG=""; [ "$SKIP" = 1 ] && SKIPARG="--skip-tests"

if [ "$MODE" = mock ]; then
  say "the whole pilot on a simulated GPU -> $OUT (a rehearsal of the pipeline: no physical claim)"
  # shellcheck disable=SC2086
  closure tier0 --mock $SKIPARG --out "$OUT"; RC=$?
  TRIAL="$OUT/T1-smoke"
else
  RUN=()
  if [ "$(id -u)" -ne 0 ]; then
    if [ "$SUDO" = auto ] && command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
      RUN=(sudo -E env "PATH=$PATH")
      echo "using sudo (it asks for no password here), so that the probe can try clock and power-limit variants"
    else
      echo "running without root: clock and power-limit variants are dropped and noted, and the slack the probe"
      echo "reports is then a lower bound. For the full probe: sudo -E env PATH=\"\$PATH\" bash scripts/run_anywhere.sh --hardware ..."
    fi
  fi
  say "the pilot on GPU $GPU, $PROFILE trial -> $OUT (exclusive use of that GPU until it finishes)"
  # shellcheck disable=SC2086
  ${RUN[@]+"${RUN[@]}"} "$PYBIN" -m closure.cli tier0 --confirm-hardware --gpu "$GPU" --trial-profile "$PROFILE" $SKIPARG --out "$OUT"; RC=$?
  TRIAL="$OUT/T1-$PROFILE"
  if [ "$MOCKRUN" = 1 ] && [ -f "$OUT/probe.json" ] \
     && ! "$PYBIN" -c 'import sys, torch; sys.exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
    echo "note: no CUDA device here, so the mock training run is skipped (on a CPU it would take hours)"
  elif [ "$MOCKRUN" = 1 ] && [ -f "$OUT/probe.json" ]; then
    say "A Narrow Path's mock training run on the same GPU -> $OUT/mock-run"
    ${RUN[@]+"${RUN[@]}"} "$PYBIN" -m closure.cli treaty mock-run --device "cuda:$GPU" --probe "$OUT/probe.json" \
      --budget-flop 1e16 --dim 4096 --layers 8 --batch 2048 --out "$OUT/mock-run" \
      || echo "note: the mock training run did not finish; the pilot's own result is unaffected"
  fi
  if [ ${#RUN[@]} -gt 0 ]; then sudo chown -R "$(id -u):$(id -g)" "$OUT" 2>/dev/null || true; fi
fi

say "result"
if [ -f "$OUT/tier0_bundle.tar.gz" ]; then
  echo "summary:  $OUT/SUMMARY.md"
  echo "bundle:   $OUT/tier0_bundle.tar.gz"
  echo "sha256:   $(sha256_of "$OUT/tier0_bundle.tar.gz")"
  [ -f "$OUT/mock-run/drill.json" ] && echo "drill:    $OUT/mock-run/drill.json"
  if [ -f "$TRIAL/results.json" ]; then
    echo
    echo "check it again yourself, from the files alone:"
    echo "  $PYBIN -m closure.cli verify $TRIAL         # hash chain, signature, commitments"
    echo "  $PYBIN -m closure.cli reanalyze --run $TRIAL   # the signed results, recomputed from raw.npz"
    echo "  $PYBIN -m closure.cli criteria --run $TRIAL    # the pre-registered rules, read off the results"
  fi
  echo
  if [ "$MODE" = mock ]; then
    echo "This was the pipeline on a simulated GPU. It shows that the code installs and runs end to end on this machine"
    echo "and that its evidence verifies; it says nothing about any real GPU. On a machine with an NVIDIA GPU:"
    echo "  bash scripts/run_anywhere.sh --hardware"
  else
    echo "To add this run to the public record, send the bundle (and drill.json if there is one) back to whoever asked"
    echo "you to run it, or open an issue at https://github.com/AnonRish/plan-a-closure/issues and attach it. Every"
    echo "run is published whatever it shows. Do not send $TRIAL/signing_key.bin: it is this run's private key, and it"
    echo "is left out of the bundle on purpose."
  fi
else
  echo "no bundle was written: the lines above say where it stopped"
fi
exit "$RC"
