#!/usr/bin/env python3
"""Diagnostic tool for the first real NVIDIA hardware run of this
project. Takes real `nvattest collect-evidence` output and reports,
unambiguously, which evidence shape it actually is -- resolving the
"evidences vs evidence_list" question docs/hardware/nvat-integration.md
found in NVIDIA's documentation but could not confirm without real
hardware.

This is a REAL tool, not a stand-in: it does not require modifying
frontier_verify source to run, and it produces a clear, copy-pasteable
result for docs/hardware/nvidia-validation-report.md.

Usage:
    nvattest collect-evidence --device gpu > real_evidence.json
    python3 confirm_evidence_shape.py real_evidence.json
"""
from __future__ import annotations

import json
import sys


def diagnose(raw: dict) -> None:
    top_level_keys = sorted(raw.keys())
    print(f"Top-level keys found: {top_level_keys}")

    has_evidences = "evidences" in raw
    has_evidence_list = "evidence_list" in raw

    if has_evidences and has_evidence_list:
        print(
            "\nBOTH 'evidences' and 'evidence_list' present -- unexpected, "
            "given docs/hardware/nvat-integration.md's research found these "
            "as ALTERNATIVE names for the same conceptual field across the "
            "local-CLI vs. NRAS-remote paths, not as two simultaneous fields. "
            "Report this exact finding back to the project -- this contradicts "
            "current documentation and needs the docs corrected, not silently "
            "worked around."
        )
    elif has_evidences:
        print(
            "\nUses 'evidences' (plural) -- matches "
            "frontier_verify/attestations/nvidia_provider.py's "
            "parse_nvat_evidence() as currently written. Try:\n\n"
            "    from frontier_verify.attestations.nvidia_provider import NvidiaAttestationProvider\n"
            "    hw = NvidiaAttestationProvider.parse_nvat_evidence(raw, mock=False)\n"
            "    print(hw.model_dump_json(indent=2))\n"
        )
        try:
            from frontier_verify.attestations.nvidia_provider import NvidiaAttestationProvider

            hw = NvidiaAttestationProvider.parse_nvat_evidence(raw, mock=False)
            print("Parsed successfully:")
            print(hw.model_dump_json(indent=2))
        except ImportError:
            print(
                "(frontier_verify not importable from this script's environment -- "
                "run from the repo root with the package installed to see the "
                "actual parse result, not just this shape diagnosis)"
            )
        except Exception as e:  # noqa: BLE001 -- deliberate: this is a diagnostic
            # tool whose whole purpose is reporting exactly what went wrong,
            # not crashing before it can report it.
            print(f"Parsing FAILED even though the top-level key matched: {e}")
            print("This is a real finding -- the field name matches but the")
            print("internal structure doesn't. Report this back with the")
            print("redacted evidence structure (see note below).")
    elif has_evidence_list:
        print(
            "\nUses 'evidence_list' -- matches the NRAS remote-API shape "
            "docs/hardware/nvat-integration.md found in release notes, NOT "
            "the shape parse_nvat_evidence() currently expects. This is "
            "exactly the gap that document predicted. Next step: adapt "
            "parse_nvat_evidence() (or add a second parser) to handle this "
            "field name -- do not silently rename the field and pretend "
            "the original assumption was right."
        )
    else:
        print(
            "\nNeither 'evidences' nor 'evidence_list' found. This is a "
            "THIRD, previously undocumented shape. Do not guess at a fix -- "
            "record the actual top-level keys above and report them back "
            "to the project so docs/hardware/nvat-integration.md can be "
            "corrected with real data instead of research-derived assumptions."
        )

    print(
        "\nNote: when reporting findings back, redact any real certificate, "
        "nonce, or evidence byte content -- only field NAMES and STRUCTURE "
        "are needed, per this project's evidence-handling caution."
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    with open(sys.argv[1]) as f:
        raw = json.load(f)
    diagnose(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
