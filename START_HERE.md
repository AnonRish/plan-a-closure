# Start here

You received this archive so that you can check it yourself, without a meeting. It contains plan-a-closure (energy,
time, traffic and state accounting for AI 2040 Plan A's inference-only verification, plus executable versions of the
Plan A and hardwired-pause numbers) and 13 related repositories under `external/`.

Nothing here demonstrates a physical claim yet. Eight shakedown runs on Tesla T4s are published whatever they showed
(`results/README.md`, `docs/DEVIATIONS.md`); everything that needs H100-class hardware and an independent power meter
is labelled hardware-gated, and the trial that would decide it is pre-registered in `docs/PREREGISTRATION.md`.
`docs/VERIFY_IT_YOURSELF.md` says what each step below shows and what none of them can.

## In three minutes, without a GPU

```bash
bash scripts/run_anywhere.sh     # makes ./.venv, installs, runs the whole pilot on a simulated GPU, verifies its evidence
```

## Without a GPU (about 15 minutes, any Linux or macOS machine with Python 3.10+)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest                          # this repository's tests, including every published hardware bundle re-read
python results/record.py        # the hardware runs on record, as one table, from the bundles
closure claims                  # Plan A's numbers, re-derived (52 of 56 reproduce; README.md discusses the other 4)
closure pause claims            # the hardwired-pause paper's numbers (111 of 114 reproduce; 3 hold under a stated reading)
closure coverage                # checks the Plan A matrix and prints its status counts (docs/PLAN_A_COVERAGE.md)
closure external check          # the vendored repositories are the trees that were tested
closure treaty coalition         # the middle-powers agreement on World Bank data (docs/TREATY_COVERAGE.md)
closure treaty coverage          # MIRI's draft agreement and FLI's Draft Articles, article by article
closure treaty chip-auth         # FLI Annex C: how long a chip runs on after its authorizations stop
closure treaty mock-run --budget-flop 4e11   # A Narrow Path's mock training run, on CPU
```

To run the vendored repositories' own suites as well (about 10 more minutes): `pip install -e ".[hw,external]"` and
`closure external test --install` (details in `external/README.md`).

## With one GPU (Tier 0: about 2 hours 20 minutes of an exclusive allocation)

```bash
bash scripts/run_anywhere.sh --check       # one minute: which steps would run on each GPU here, and why not where not
bash scripts/run_anywhere.sh --hardware    # the pilot; --profile medium (5 h 40 min) or long (11 h) reads the decision rules
```

It is one unattended command underneath, `closure tier0`, which logs every step and writes a bundle to send back
(`docs/OPERATOR_TIER0.md`). The bundle leaves out the run's private key; do not send `signing_key.bin`. Every run so
far was on a T4: a run on any other GPU is the first of its kind.

No GPU of your own: `docs/GPU_ACCESS.md` lists the free and nearly free routes. With a Modal account (its free plan
includes $30 of compute a month) the pilot runs on an H100, H200, B200 or B300 from your own computer:

```bash
pip install modal && modal setup
modal run scripts/modal_tier0.py --gpu H100 --check          # a minute or two first
modal run --detach scripts/modal_tier0.py --gpu H100         # the smoke pilot
```

## Sending results back

Reply to the message that brought you the archive, or open an issue at
https://github.com/AnonRish/plan-a-closure/issues, with the bundle (`tier0_bundle.tar.gz` in the run's folder) or the
output of the commands above. Results are published whatever they show.
