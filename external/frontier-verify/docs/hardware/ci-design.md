# Real-Hardware CI Design

**Execution status: NOT VERIFIED.** No self-hosted GPU runner exists for
this project. Everything below is a design, not a running pipeline. Do
not fake this in ordinary CI -- `tests/hardware/nvidia/` already skips
cleanly on any runner without a GPU, which is the correct behavior for
the CI this project actually has today.

## Design

A separate workflow, distinct from the main test suite, triggered only on
a self-hosted runner labeled for GPU access:

```yaml
# .github/workflows/hardware-ci.yml (NOT CREATED -- design only)
on:
  workflow_dispatch:        # manual trigger, not automatic on every push --
                             # a GPU runner is scarce/expensive infrastructure,
                             # not something to burn on every commit
runs-on: [self-hosted, gpu, nvidia-hopper]   # runner labeling requirement
jobs:
  hardware-tests:
    steps:
      - run: nvidia-smi -L
      - run: nvattest --version
      - run: pip install -e ".[dev]"
      - run: pytest tests/hardware/nvidia/ -v
```

## Requirements this design assumes, none of them provisioned

- **Hardware availability**: a real, dedicated (or carefully scheduled
  shared) Hopper-or-later GPU runner. Not provisioned.
- **Runner labeling**: `self-hosted, gpu, nvidia-hopper` as shown above --
  a real self-hosted GitHub Actions (or equivalent) runner registration.
  Not provisioned.
- **Secure secrets**: an NGC service key for remote/NRAS attestation
  testing (`docs/hardware/nvat-integration.md`), stored as a CI secret,
  never in source. Not provisioned -- there is no such key.
- **Attestation trust roots**: the runner needs whatever certificate
  trust store NVIDIA's attestation chain validation requires, kept
  current. Not provisioned.
- **Artifact capture**: real evidence/claims JSON from actual test runs
  should be captured as CI artifacts (redacted of anything sensitive) so
  a schema mismatch is debuggable without re-running on scarce hardware
  each time. Not provisioned.
- **Failure handling**: a hardware CI failure should be distinguishable
  from "runner unavailable" (infrastructure problem) versus "attestation
  genuinely failed" (a real finding) -- the design above doesn't yet
  specify how, because building that distinction properly requires
  observing real failure modes first, which requires the runner this
  design doesn't have.

## Why this stays a design document, not a workflow file

Committing a `.github/workflows/hardware-ci.yml` that references
`self-hosted, gpu, nvidia-hopper` runners that don't exist would either
silently never run (harmless but misleading -- looks like coverage that
isn't there) or actively break CI for anyone who forks this repository
without that runner labeling available. Neither is better than a design
document that says plainly what's needed and that none of it exists yet.
