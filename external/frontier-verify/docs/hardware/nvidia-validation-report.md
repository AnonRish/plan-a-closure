# NVIDIA Hardware Validation Report

**STATUS: NOT EXECUTED. No real NVIDIA hardware has run any part of this
project.** Every field below is a template, not a result. This document
exists so that the moment someone with real access follows
`docs/hardware/nvidia-real-test.md`, filling in this report is the
natural next step, not a separate design task.

Per section 3 of the Phase 4 brief: "Never describe a result as 'NVIDIA
verified' without an actual execution against supported hardware." This
document contains zero such claims. Every row says `UNVERIFIED` or
`NOT RUN` because that is the truth, not because the template is
incomplete.

## Environment (fill in from the actual test machine)

| Field | Value |
|---|---|
| GPU model | UNVERIFIED |
| CPU / platform | UNVERIFIED |
| Driver version | UNVERIFIED |
| Firmware version | UNVERIFIED |
| CUDA version (if applicable) | UNVERIFIED |
| NVAT version | UNVERIFIED |
| OS | UNVERIFIED |
| Confidential Computing mode | UNVERIFIED |
| Attestation mode tested (local / remote / both) | NOT RUN |
| Verifier configuration | UNVERIFIED |
| Trust roots used | UNVERIFIED |

## Validation checklist (section 2's ten items)

| # | Item | Result |
|---|---|---|
| 1 | Hardware detection | NOT RUN |
| 2 | GPU identity | NOT RUN |
| 3 | Platform measurements | NOT RUN |
| 4 | Attestation generation | NOT RUN |
| 5 | Evidence capture | NOT RUN |
| 6 | Evidence transport | NOT RUN |
| 7 | Evidence validation | NOT RUN |
| 8 | Policy evaluation | NOT RUN |
| 9 | Receipt generation | NOT RUN |
| 10 | Independent receipt verification | NOT RUN |

## Local vs. remote attestation (section 4)

Not tested. `docs/hardware/nvat-integration.md`'s research finding --
that the local CLI's evidence format (`evidences`) and the NRAS remote
API's format (`evidence_list`) genuinely differ -- means this comparison
is not a formality once real hardware is available; it may require two
separate code paths, not one parser handling both. See that document's
"Important correction" section before assuming either format applies to
what real hardware produces.

## Exact commands and results

None recorded -- see `docs/hardware/nvidia-real-test.md` for the exact
commands to run. This section should be filled in with copy-pasted real
terminal output, not summarized, the first time this report is completed.

## Failures and limitations

None recorded, because nothing has run.

## How to complete this report for real

1. Follow `docs/hardware/nvidia-real-test.md` steps 1-4 exactly.
2. Replace every `UNVERIFIED`/`NOT RUN` above with the actual value or
   actual command output.
3. If any step fails, record the failure verbatim in "Failures and
   limitations" above -- a documented failure is a more valuable
   contribution to this project than a silently-abandoned attempt.
4. Update `docs/ai2040-gap-analysis-phase4.md` rows 5, 7, 12, 13, 14, 17,
   22 (the ones a real hardware result could plausibly move from YELLOW
   toward GREEN) to reflect what was actually found -- do not move a row
   to GREEN without this report backing it up with real command output.
