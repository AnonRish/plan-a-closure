# Real NVIDIA Hardware Test Instructions

For someone with actual access to NVIDIA hardware this project's own
development environment does not have. If you're reading this because
you have that access: thank you, this is the single highest-value
external contribution this project can currently receive.

## Requirements (per `docs/hardware/nvat-integration.md`)

- Hopper-generation or later NVIDIA GPU
- Confidential Computing enabled
- Ubuntu 22.04 or 24.04, running as a Confidential VM (CVM)
- NVIDIA Management Library (NVML) installed via the standard driver
- `nvattest` CLI installed (see `docs/hardware/nvat-integration.md` for
  the build-from-source dependency list, or use a prebuilt release from
  NVIDIA's Attestation SDK downloads page)

## Step 1: confirm the environment

```bash
nvidia-smi -L                          # confirms a GPU is visible at all
nvidia-smi conf-compute -f             # confirms Confidential Computing state
nvattest --version                     # confirms the CLI is installed
```

## Step 2: run the hardware test harness

```bash
cd frontier-verify
pip install -e ".[dev]"
pytest tests/hardware/nvidia/ -v
```

On a properly configured machine, `test_hardware_detection_smoke_test`
and `test_nvattest_cli_invocation` should now PASS instead of skip.
`test_real_evidence_collection` and
`test_real_evidence_matches_parser_expectations` require Confidential
Computing specifically to be enabled, not just a GPU present.

## Step 3: confirm evidence shape (do this BEFORE trusting the parser)

```bash
nvattest collect-evidence --device gpu > real_evidence.json
python3 -m json.tool real_evidence.json
```

Compare the top-level keys against
`docs/hardware/nvat-integration.md`'s "Important correction" section --
specifically, does the output use `evidences` (the shape
`frontier_verify/attestations/nvidia_provider.py`'s
`parse_nvat_evidence()` currently expects) or `evidence_list` (the shape
NRAS's v3 remote API release notes document)? This project's research
this phase found evidence that BOTH names exist in NVIDIA's documentation
for different code paths (local CLI vs. remote NRAS), but could not
confirm which one `nvattest collect-evidence` actually produces without
running it -- which is exactly what this step is for.

```bash
python3 -c "
import json
from frontier_verify.attestations.nvidia_provider import NvidiaAttestationProvider
raw = json.load(open('real_evidence.json'))
hw = NvidiaAttestationProvider.parse_nvat_evidence(raw, mock=False)
print(hw.model_dump_json(indent=2))
"
```

If this raises `ValueError: no 'evidences' entries`, the real output uses
`evidence_list` instead -- update
`docs/hardware/nvat-integration.md`'s findings and
`nvidia_provider.py`'s parser accordingly, then remove the `xfail` marker
on `test_real_evidence_matches_parser_expectations` in
`tests/hardware/nvidia/test_real_attestation.py`.

## Step 4: report back

Whatever you find -- confirmed compatible, confirmed incompatible with a
specific field mismatch, or something this document didn't anticipate --
is genuinely useful information for this project regardless of the
outcome. A confirmed incompatibility is not a failure; it's exactly the
kind of finding `docs/hardware/nvat-integration.md` exists to be updated
with.

## What this does NOT cover yet

Certificate chain validation, NRAS remote attestation, and the richer
"claims" schema (post-verification booleans) documented in
`docs/hardware/nvat-integration.md`'s "richer discovery" section are all
still unimplemented in `nvidia_provider.py` regardless of what this test
pass confirms. Getting evidence COLLECTION working is the first step, not
the whole workstream.
