# Start here

You received this archive so that you can check it yourself, without a meeting. It contains plan-a-closure (energy,
time, traffic and state accounting for AI 2040 Plan A's inference-only verification, plus executable versions of the
Plan A and hardwired-pause numbers) and 13 related repositories under `external/`.

Nothing here demonstrates a physical claim yet. Everything that needs a GPU is labelled hardware-gated, and the trial
that would decide it is pre-registered in `docs/PREREGISTRATION.md`.

## Without a GPU (about 15 minutes, any Linux or macOS machine with Python 3.10+)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest                          # this repository's tests
closure claims                  # Plan A's numbers, re-derived (52 of 56 reproduce; README.md discusses the other 4)
closure pause claims            # the hardwired-pause paper's numbers (111 of 114 reproduce; 3 hold under a stated reading)
closure coverage                # checks the Plan A matrix and prints its status counts (docs/PLAN_A_COVERAGE.md)
closure external check          # the vendored repositories are the trees that were tested
```

To run the vendored repositories' own suites as well (about 10 more minutes): `pip install -e ".[hw,external]"` and
`closure external test --install` (details in `external/README.md`).

## With one GPU (Tier 0: about 2 hours of an exclusive allocation)

Follow `docs/OPERATOR_TIER0.md`. It is one unattended command, `closure tier0`, which logs every step and writes a
bundle to send back. The bundle leaves out the run's private key; do not send `signing_key.bin`.

## Sending results back

Reply to the message that brought you the archive with the bundle (`runs/tier0/tier0_bundle.tar.gz`) or the output of
the commands above. Results are published whatever they show.
