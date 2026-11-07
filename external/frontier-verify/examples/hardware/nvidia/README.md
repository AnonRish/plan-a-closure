# NVIDIA Hardware Example

For someone with real NVIDIA hardware access -- see
`docs/hardware/nvidia-real-test.md` for full setup instructions. This
directory has one real, tested tool:

```bash
nvattest collect-evidence --device gpu > real_evidence.json
python3 confirm_evidence_shape.py real_evidence.json
```

Resolves the "does real hardware use `evidences` or `evidence_list`"
question `docs/hardware/nvat-integration.md` found in NVIDIA's
documentation but could not confirm without real hardware. Tested against
all three possible outcomes (`tests` were run manually against the
synthetic fixture in three configurations before this tool was
committed -- see the tool's own source comments) -- this is not
speculative tooling shipped untested.

## What this does NOT include

A real evidence fixture. `frontier_verify/attestations/fixtures/nvidia_evidence_synthetic.json`
remains synthetic (fabricated values, real field shape) -- this project
has no real hardware to generate a genuine one from. If you run
`confirm_evidence_shape.py` against real output, please consider
contributing a REAL fixture back (with certificate/evidence bytes
redacted per the tool's own printed reminder) so future work doesn't have
to guess at the shape either.
