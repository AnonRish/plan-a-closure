"""
§22, part 3: the tap-installation registry -- reusing §21b's exact
TamperEvidentLog / LogEntry construction (Ed25519 signing, hash-chained,
imported unmodified from tamper_log.py) with a payload shape specific to a
tap installation record instead of a verification report. §21b already
demonstrated, against a real tampering attempt, that this construction
catches payload edits via both a broken signature AND a broken hash-chain
link. That property isn't re-derived here -- it's re-applied, to confirm
the reuse is actually load-bearing for a genuinely different payload
shape, not just a claim that it would work.
"""
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tamper_log import TamperEvidentLog

if __name__ == "__main__":
    priv = Ed25519PrivateKey.generate()
    registry = TamperEvidentLog(priv)

    print("=" * 90)
    print("Building a real tap-installation registry: 5 taps across 2 facilities,")
    print("each entry carrying its physical seal's serial number")
    print("=" * 90)
    installs = [
        {"tap_id": "FAC001-G0-0001", "facility_id": "FAC001", "granularity": "facility", "seal_serial": "TID-88213-A"},
        {"tap_id": "FAC001-G1-0001", "facility_id": "FAC001", "granularity": "rack", "seal_serial": "TID-88214-A"},
        {"tap_id": "FAC001-G1-0002", "facility_id": "FAC001", "granularity": "rack", "seal_serial": "TID-88215-A"},
        {"tap_id": "FAC002-G0-0001", "facility_id": "FAC002", "granularity": "facility", "seal_serial": "TID-91004-A"},
        {"tap_id": "FAC002-G1-0001", "facility_id": "FAC002", "granularity": "rack", "seal_serial": "TID-91005-A"},
    ]
    for rec in installs:
        registry.append({"event": "install", **rec})

    ok, msg = registry.verify_integrity()
    print(f"Baseline check: {ok} ({msg})")
    assert ok

    print()
    print("=" * 90)
    print("A later inspection re-checks FAC001-G1-0001's seal and finds a DIFFERENT serial")
    print("than what's on file -- the mechanism this registry exists to make legible, not")
    print("seal-forgery-resistance itself, which is a physical-hardware property no software")
    print("log can supply (Johnston et al.'s own finding: cost didn't predict seal security")
    print("across the 94 seals their team tested and defeated -- see write-up)")
    print("=" * 90)
    registry.append({
        "event": "inspection", "tap_id": "FAC001-G1-0001",
        "seal_serial_observed": "TID-88214-B", "matches_registry": False,
    })
    ok, msg = registry.verify_integrity()
    print(f"Registry still verifies -- this is an HONEST new entry reporting a real-world")
    print(f"discrepancy, not tampering, and the log's job is to record it faithfully, not")
    print(f"reject it: {ok} ({msg})")
    assert ok, "an honest report of a seal mismatch must not itself break the log"

    print()
    print("=" * 90)
    print("The actual attack this registry defends against: retroactively editing the")
    print("EXISTING install record to make the mismatch above look like a data-entry error")
    print("instead of a real tamper event -- covering physical tampering by also tampering")
    print("with the paper trail")
    print("=" * 90)
    target_index = 2  # entries: [0]=genesis, [1]=FAC001-G0-0001, [2]=FAC001-G1-0001, ...
    assert registry.entries[target_index].payload["tap_id"] == "FAC001-G1-0001"
    print(f"entry {target_index} payload BEFORE: {registry.entries[target_index].payload}")
    registry.entries[target_index].payload["seal_serial"] = "TID-88214-B"  # retroactively "matching"
    print(f"entry {target_index} payload AFTER:  {registry.entries[target_index].payload}")
    ok, msg = registry.verify_integrity()
    print(f"Post-tamper check: {ok} ({msg})")
    assert not ok, "retroactively editing an install record must be caught"

    entry_sig_valid = registry.entries[target_index].verify(registry.public_key)
    next_chain_valid = registry.entries[target_index + 1].prev_hash == registry.entries[target_index].entry_hash()
    print(f"entry {target_index} signature still valid against its (now-changed) content: {entry_sig_valid} (must be False)")
    print(f"entry {target_index + 1}'s stored prev_hash still matches entry {target_index}'s (now-changed) hash: {next_chain_valid} (must be False)")
    assert not entry_sig_valid and not next_chain_valid

    print()
    print("Caught for the identical reason §21b's own tamper test caught it -- no new")
    print("mechanism was needed, because §21b's log already had this property. This file")
    print("only confirms it holds for a tap-registry-shaped payload too, rather than just")
    print("asserting that reuse is valid.")
