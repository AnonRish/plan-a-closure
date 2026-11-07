# Phase 4 Baseline

Frozen as git tag `v0.4.0-phase4`, commit `9394193`. Unlike the Phase 3
baseline, freezing this one required no new commit -- `git status` at the
start of Phase 5 showed a clean tree identical to Phase 4's last commit,
confirmed directly rather than assumed. Nothing changed between phases
because nothing COULD change without the two blockers named in every
report since Phase 4: real hardware, and an independent human reviewer.

## Test count at freeze

123 passed, 4 skipped. Unchanged from Phase 4's own count -- re-run at
the start of Phase 5 to confirm, not carried forward from memory.

## Package hash

Recomputable directly from the tag:

```bash
git checkout v0.4.0-phase4
python3 -m build --wheel
sha256sum dist/*.whl
```

Not recorded as a fixed value here, since `docs/research/reproducible-builds.md`
already establishes that a fixed `SOURCE_DATE_EPOCH` is required for the
hash to be meaningful across separate build invocations -- pinning one
number here without that context would misrepresent what was actually
demonstrated.

## Known limitations at freeze, identical to Phase 4's

No real NVIDIA hardware, no real Triton instance, no independent human
review, no deployment outside this development environment. Restated here
only because section 1 of the Phase 5 brief asks for it explicitly --
see `docs/releases/phase-3-baseline.md` for the same list one phase
earlier, itself also unchanged from Phase 2's version. Three consecutive
freeze points with an identical limitations list is itself the finding:
software work alone cannot move this list.
