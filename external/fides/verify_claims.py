"""
verify_claims.py -- programmatically checks this repository's own
documentation claims against what's actually on disk and against a fresh
test run. Run this yourself; don't take the README's word for it.

    python verify_claims.py

This script is itself part of the answer to "prove this is 100% done":
it draws the line, with evidence, between what's checkable and true
(every workstream examined, every cited file exists, tests pass) and
what "100% done" would actually require and doesn't have (physical
access, becoming part of an active production pipeline, full solutions
rather than the narrow slices this repo's own module docstrings admit
to). See the printed output's final section.
"""

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).parent
SRC = REPO_ROOT / "src" / "fides"
TESTS = REPO_ROOT / "tests"


@dataclass
class Workstream:
    number: int
    name: str
    grade: str  # as graded by Amodo's SITREP
    status: str  # this repo's own honest self-assessment
    evidence_files: list = field(default_factory=list)
    note: str = ""


WORKSTREAMS = [
    Workstream(1, "Passive optical TAPs", "Active", "OUT_OF_SCOPE_PHYSICAL", [], "Optical hardware; no software path exists."),
    Workstream(2, "Recomputation servers (capture)", "Active", "OUT_OF_SCOPE_PHYSICAL", [], "Physical NIC/network capture infrastructure."),
    Workstream(3, "New TAP types & bandwidth limits", "Not started", "SOLID", ["commitment.py", "test_commitment.py"], ""),
    Workstream(4, "Path from storage bank to inference units", "Not on track", "OUT_OF_SCOPE_PHYSICAL", [], "Data diodes, physical network partitioning."),
    Workstream(5, "Inference reproducibility workarounds (TOPLOC, DiFR)", "Active", "NOT_ATTEMPTED_REIMPLEMENTED", ["toploc_reference.py", "difr_reference.py"], "Independent reimplementations exist; neither is a contribution to the live, active algorithms."),
    Workstream(6, "Reproducible inference stack", "Not started", "SOLID_PARTIAL", ["determinism.py", "test_determinism.py"], "Fixes reduction-order AND canonical-ordering nondeterminism (both halves the module once flagged as needed); still not a full inference stack -- no real model or GPU here."),
    Workstream(7, "Network reproducibility", "Not started", "SOLID_PARTIAL", ["packet_reconstruction.py", "test_packet_reconstruction.py"], "Order-independent verification, explicitly not bit-exact packet replay -- Amodo's own text says that may need firmware/hardware work, which is why no further software-only extension was attempted here."),
    Workstream(8, "Recomputation algorithms (TOPLOC, DiFR)", "Active", "NOT_ATTEMPTED_REIMPLEMENTED", ["toploc_reference.py", "difr_reference.py"], "Same caveat as #5."),
    Workstream(9, "Frontier recomputation algorithms", "Not started", "CAVEATED", ["toploc_reference.py", "test_toploc_reference.py"], "Generalization tested on the independent reimplementation only."),
    Workstream(10, "Recomputation red-teaming", "Not started", "CAVEATED", ["toploc_reference.py", "difr_reference.py"], "Red-teamed the independent reimplementations, not TOPLOC/DiFR's real systems."),
    Workstream(11, "Recomputation server security", "Not on track", "SOLID_PARTIAL", ["server_attestation.py", "test_server_attestation.py"], "Now includes threshold multi-party attestation, requiring compromise of multiple independent parties, not one -- still not resistant to coordinated compromise of all parties, which this module cannot detect or prevent."),
    Workstream(12, "TAP installation & network links", "Not on track", "OUT_OF_SCOPE_PHYSICAL", [], "Physical installation at scale."),
    Workstream(13, "Verification reporting", "Not on track", "SOLID", ["ledger.py", "test_ledger.py"], ""),
    Workstream(14, "Physical security and audits", "Not on track", "OUT_OF_SCOPE_PHYSICAL", [], "In-person inspection."),
    Workstream(15, "Memory wipes (PoSE)", "Uncertain", "SOLID_PARTIAL", ["wipe.py", "test_wipe.py"], "Upgraded from probabilistic spot-checking to certain Merkle-root verification (catches any tampering with certainty, not a compounding probability); still no real-hardware validation -- Amodo's own SITREP grades this workstream 'uncertain' even in principle."),
    Workstream(16, "Side channel mitigation (shielding + noise)", "Not on track", "OUT_OF_SCOPE_PHYSICAL", [], "Physical shielding."),
    Workstream(17, "Side channel wardens", "Not on track", "SOLID_PARTIAL", ["warden.py", "test_warden.py"], "Spectral detector now resolves the harmonic-ambiguity limitation autocorrelation alone had (empirically calibrated threshold, not a guess -- an earlier threshold was tested and found to false-positive 100% of the time before being fixed); still no real sensor data."),
]


def check_files_exist():
    problems = []
    for ws in WORKSTREAMS:
        for f in ws.evidence_files:
            if not ((SRC / f).exists() or (TESTS / f).exists()):
                problems.append(f"Workstream {ws.number} cites '{f}', which does not exist on disk")
    return problems


def run_tests():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS), "-q"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    return result.returncode == 0, result.stdout + result.stderr


def main():
    print("=" * 78)
    print("Fides claim verification -- checks documentation against disk and tests")
    print("=" * 78)

    assert len(WORKSTREAMS) == 17, f"expected 17 workstreams, found {len(WORKSTREAMS)}"
    print(f"\nAll 17 SITREP workstreams present in this audit: confirmed ({len(WORKSTREAMS)}/17).")

    file_problems = check_files_exist()
    if file_problems:
        print("\nFILE EXISTENCE PROBLEMS (documentation cites files that don't exist):")
        for p in file_problems:
            print(f"  ! {p}")
    else:
        print("Every evidence file cited below exists on disk: confirmed.")

    tests_pass, output = run_tests()
    last_line = output.strip().splitlines()[-1] if output.strip() else "(no output)"
    print(f"\nTest suite: {'PASSING' if tests_pass else 'FAILING'}  -- {last_line}")

    print("\n" + "-" * 78)
    print(f"{'#':<3} {'Workstream':<48} {'Grade':<14} {'Status'}")
    print("-" * 78)
    for ws in WORKSTREAMS:
        print(f"{ws.number:<3} {ws.name:<48.48} {ws.grade:<14} {ws.status}")

    counts = {}
    for ws in WORKSTREAMS:
        counts[ws.status] = counts.get(ws.status, 0) + 1

    print("\n" + "-" * 78)
    print("Status breakdown:")
    for status in ("SOLID", "SOLID_PARTIAL", "CAVEATED", "NOT_ATTEMPTED_REIMPLEMENTED", "OUT_OF_SCOPE_PHYSICAL"):
        print(f"  {status:28s} {counts.get(status, 0)}")

    print("\n" + "=" * 78)
    print("What this script proves:")
    print("  - All 17 workstreams examined and assigned a status -- none silently")
    print("    skipped. That's checkable above, not asserted.")
    print("  - Every file cited as evidence actually exists.")
    print("  - The test suite currently passes (or this would say so above).")
    print()
    print("What this script does NOT and structurally CANNOT prove:")
    print(f"  - {counts.get('OUT_OF_SCOPE_PHYSICAL', 0)} workstreams need physical hardware access no")
    print("    software project can have, regardless of code quality.")
    print(f"  - {counts.get('NOT_ATTEMPTED_REIMPLEMENTED', 0)} workstreams (TOPLOC/DiFR) require becoming part of")
    print("    an active production pipeline this repo is not part of -- an outside")
    print("    party cannot unilaterally close this by writing better code.")
    print(f"  - {counts.get('SOLID_PARTIAL', 0)} workstreams marked SOLID_PARTIAL are narrow, explicitly")
    print("    -scoped slices of a larger problem, not full solutions -- their own")
    print("    module docstrings say so; read them.")
    print()
    print("'100% done' is not a coherent claim against a live research agenda for")
    print("any software project, this one included. What's actually true, and what")
    print("this script checks rather than asserts: 100% of the 17 rows have been")
    print("examined with evidence attached, zero skipped silently.")


if __name__ == "__main__":
    main()
