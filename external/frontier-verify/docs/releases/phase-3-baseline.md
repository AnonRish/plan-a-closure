# Phase 3 Baseline

Frozen as git tag `v0.3.0-phase3-baseline`, commit `2634ec6`, before any
Phase 4 work began. This document is what section 1 of the Phase 4 brief
asks for; the tag is the actual freeze mechanism, this file is the record
of what it means.

## Test count at freeze

104 passed, 4 skipped (hardware tests, correctly skipping without a GPU).
Zero lint findings. Zero broken documentation cross-references (checked
via the automated consistency scan described in `docs/api-design.md`'s
neighboring phase reports).

## Protocol version at freeze

`Receipt.receipt_version = "0.1.0"` -- unchanged since Phase 1. The
receipt WIRE FORMAT has not changed across three phases of substantial
internal changes (auth, revocation, storage backend) specifically because
none of those changes touched what a receipt contains or how it's signed
-- see `docs/receipt-specification.md`. This is worth stating plainly at
a freeze point: protocol stability and internal implementation churn are
different axes, and this project has kept the former stable while the
latter changed substantially.

## Known limitations at freeze, unchanged by anything in this document

- No real NVIDIA hardware has ever executed this code.
- No real Triton or vLLM instance has ever executed this code.
- No real recomputation of actual ML inference exists -- only sampling
  logic tested against toy/small numerical stand-ins.
- No human who did not write this system has reviewed it.
- Nothing in this repository has ever been deployed, run, or used outside
  the single development environment (and now, git history) it exists in.

## Why freeze now, specifically

Section 1 of the Phase 4 brief asks for this before "making significant
architectural changes." Phase 4's actual content is different in kind
from Phases 1-3: it's about obtaining evidence from OUTSIDE this
environment (real hardware, real independent review), not building more
inside it. A frozen, tagged baseline is what makes it possible to later
say precisely "here's what existed before real-world validation began,"
which is exactly the comparison a real hardware test or a real external
review would need to be meaningful against.

## How to actually verify this baseline yourself

```bash
git log --oneline v0.3.0-phase3-baseline
git checkout v0.3.0-phase3-baseline
pip install -e ".[dev,triton]"
pytest -q   # should show: 104 passed, 4 skipped
```
