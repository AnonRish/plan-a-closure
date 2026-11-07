"""
§27: "The open problem is proving the combination is sound, i.e. that a
policy set actually enforces the independence between trust roots it
claims to, rather than quietly collapsing back to one" -- the Verification
Plan supplement's own words for exactly this section's job. Rather than
build a fresh toy example, this file audits this document's OWN prior
code for the failure the sentence describes, because a self-referential
finding is a stronger demonstration than an invented one.

The finding: §24's weight_transport.py __main__ does this --

    auditor_key = Ed25519PrivateKey.generate()
    training_registry = ApprovalRegistry(auditor_key)
    release_chain = ReleaseChain(auditor_key, training_registry)

ONE key, instantiating BOTH the §23 training-workload-approval authority
AND the §24 release authority. Nothing in either class is broken -- both
do exactly what they were built and tested to do. The bug is compositional:
the calling code treated two decisions the document's own narrative
clearly wants to be independent (an audit team confirming a training run
stayed within declared bounds; a separate release/safety process deciding
whether to actually ship weights after evaluation) as if they were one
authority, because it was convenient to reuse the same key object.
"""
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature
from tamper_log import TamperEvidentLog
from workload_approval import ApprovalRegistry
import hashlib


def attempt_forge_approval(attacker_key, cert_hash, workload_id, real_registry):
    """An attacker who holds SOME key tries to forge a training-workload
    approval, appending directly to the log a legitimate verifier would
    check. Signed with whatever key the attacker actually has -- the
    point under test is whether that signature validates against the
    registry's real public key, not whether the attacker can physically
    reach the log (a distribution problem this file isn't about)."""
    forged_log = TamperEvidentLog(attacker_key)
    forged_log.append({"event": "approve", "cert_hash": cert_hash, "workload_id": workload_id,
                        "auditor_id": "auditor_04", "issued_seed": 999999})
    forged_entry = forged_log.entries[-1]
    try:
        real_registry.log.public_key.verify(forged_entry.signature, bytes.fromhex(forged_entry.entry_hash()))
        return True  # signature validates against the REAL registry's trusted key
    except InvalidSignature:
        return False


if __name__ == "__main__":
    print("=" * 92)
    print("1. Reproducing §24's ACTUAL setup: one key, two logically-distinct roles")
    print("=" * 92)
    shared_key = Ed25519PrivateKey.generate()
    training_registry = ApprovalRegistry(shared_key)
    release_log = TamperEvidentLog(shared_key)  # standing in for ReleaseChain's own log,
                                                    # constructed exactly as §24 built it --
                                                    # same key, different logical purpose

    real_seed = training_registry.approve(hashlib.sha256(b"genuine_workload").hexdigest(),
                                            workload_id="genuine", auditor_id="auditor_04")
    release_log.append({"event": "release", "manifest_root": "aaaa", "auditor_id": "auditor_09"})
    print(f"  Training registry public key: {training_registry.log.public_key.public_bytes_raw().hex()[:16]}...")
    print(f"  Release log public key:       {release_log.public_key.public_bytes_raw().hex()[:16]}...")
    print(f"  Same key underneath both:     {training_registry.log.public_key.public_bytes_raw() == release_log.public_key.public_bytes_raw()}")

    print()
    print("=" * 92)
    print("2. THE ATTACK: whoever compromises this ONE key can forge BOTH roles")
    print("=" * 92)
    attacker_has = shared_key  # the compromise event: this document's own §24 code made
                                  # this the SAME key an attacker would need to steal exactly once
    forged_cert = hashlib.sha256(b"never_actually_approved_workload").hexdigest()
    can_forge_approval = attempt_forge_approval(attacker_has, forged_cert, "malicious", training_registry)
    print(f"  Attacker forges a TRAINING APPROVAL using the compromised key: accepted={can_forge_approval}")

    forged_release = TamperEvidentLog(attacker_has)
    forged_release.append({"event": "release", "manifest_root": "deadbeef", "auditor_id": "auditor_09"})
    release_forge_valid = True
    try:
        release_log.public_key.verify(forged_release.entries[-1].signature,
                                        bytes.fromhex(forged_release.entries[-1].entry_hash()))
    except InvalidSignature:
        release_forge_valid = False
    print(f"  SAME attacker forges a RELEASE decision using the SAME compromised key: accepted={release_forge_valid}")
    print(f"  One compromise, both authorities defeated: {can_forge_approval and release_forge_valid}")
    print("  This is what 'quietly collapsing back to one' actually looks like in a real")
    print("  artifact, not just as a phrase -- two decisions this document's own narrative")
    print("  wants independent, defeated by exactly one stolen key.")

    print()
    print("=" * 92)
    print("3. THE FIX, tested: independently generated keys per authority")
    print("=" * 92)
    training_key = Ed25519PrivateKey.generate()
    release_key = Ed25519PrivateKey.generate()
    hardened_training_registry = ApprovalRegistry(training_key)
    hardened_release_log = TamperEvidentLog(release_key)
    hardened_training_registry.approve(hashlib.sha256(b"genuine_workload_2").hexdigest(),
                                          workload_id="genuine2", auditor_id="auditor_04")

    print("  Attacker compromises ONLY the release key (a real, narrower breach -- e.g. the")
    print("  release/safety team's system, not the technical-audit team's)")
    attacker_has_release_only = release_key

    can_forge_release = True
    forged_release2 = TamperEvidentLog(attacker_has_release_only)
    forged_release2.append({"event": "release", "manifest_root": "cafebabe", "auditor_id": "auditor_09"})
    try:
        hardened_release_log.public_key.verify(forged_release2.entries[-1].signature,
                                                   bytes.fromhex(forged_release2.entries[-1].entry_hash()))
    except InvalidSignature:
        can_forge_release = False
    print(f"    Forging a RELEASE with the compromised release key: accepted={can_forge_release}")

    can_forge_training_now = attempt_forge_approval(attacker_has_release_only,
                                                        hashlib.sha256(b"still_never_approved").hexdigest(),
                                                        "malicious2", hardened_training_registry)
    print(f"    SAME attacker attempting to forge a TRAINING APPROVAL with the release key: accepted={can_forge_training_now}")
    assert can_forge_release and not can_forge_training_now
    print("  PASS: the compromise stayed contained to the role whose key was actually stolen.")
    print("  Not zero risk -- the release authority is still fully compromised -- but genuinely")
    print("  narrower than before, which is the entire point of composing independent roots:")
    print("  not eliminating single points of failure, bounding what any ONE of them reaches.")
