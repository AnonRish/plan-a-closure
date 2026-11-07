"""
§24b: weight transport. The Verification Plan supplement's own framing:
after evaluations are run and verified (24a), "final model approval for
release leads to the model weights being downloaded from the opaque
internal database and transported to the inference-only clusters," a
process the supplement itself calls "extremely high stakes from a model
weights theft perspective."

This is NOT §19's transport. §19 covered storage-bank-to-inference-unit,
inside one already-verified facility. This is a bigger jump: weights
crossing OUT of an R&D cluster (§23's approval regime) and INTO the
inference-only architecture this whole document has built since §1 --
between two different security domains, carrying a newly-trained,
not-yet-public, maximally valuable payload.

The real question a receiving inference-only cluster needs answered isn't
"is this transport link secure" (§19 already covers link-level design) --
it's "are these SPECIFIC bytes the ones that actually got approved,"
which needs a chain: an approved training workload (§23) produced a
checkpoint; that checkpoint's evaluations got verified (24a); a release
decision bound a specific manifest of weight-shard hashes to that
approval; and whatever bytes physically arrive get checked against that
bound manifest before anything deploys. Every link below is built on
something this document already has, not invented fresh for this file.
"""
import hashlib
import os
import secrets
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tamper_log import TamperEvidentLog
from workload_approval import ApprovalRegistry


def h(a: bytes, b: bytes) -> bytes:
    return hashlib.sha256(a + b).digest()


class ManifestTree:
    """Merkle tree over weight-shard hashes. Same construction §4's Rust
    EpochTree already built and tested (build/proof/verify_inclusion, odd
    node counts duplicate the last node at each level) -- reimplemented in
    Python here because this section's chain lives on the Python side
    (approval registry, eval verification), not re-derived from scratch."""

    def __init__(self, shard_hashes):
        assert shard_hashes, "empty manifest -- caller's job to reject before this"
        self.leaves = list(shard_hashes)
        levels = [self.leaves]
        cur = self.leaves
        while len(cur) > 1:
            nxt = []
            for i in range(0, len(cur), 2):
                left = cur[i]
                right = cur[i + 1] if i + 1 < len(cur) else cur[i]
                nxt.append(h(left, right))
            levels.append(nxt)
            cur = nxt
        self.levels = levels
        self.root = cur[0]

    def proof(self, index):
        proof, idx = [], index
        for level in self.levels[:-1]:
            sib = level[idx + 1] if idx % 2 == 0 and idx + 1 < len(level) else level[idx - 1] if idx % 2 else level[idx]
            proof.append(sib)
            idx //= 2
        return proof

    @staticmethod
    def verify_inclusion(leaf, index, proof, root):
        cur, idx = leaf, index
        for sib in proof:
            cur = h(cur, sib) if idx % 2 == 0 else h(sib, cur)
            idx //= 2
        return cur == root


def manifest_root_for_shards(shard_bytes_list):
    """What both the releasing auditor AND the receiving cluster compute
    independently -- the whole point is that neither has to trust the
    other's hash, only recompute it themselves over whatever bytes they
    actually have in hand."""
    hashes = [hashlib.sha256(b).digest() for b in shard_bytes_list]
    return ManifestTree(hashes).root, hashes


class ReleaseChain:
    """Binds a release decision to (a) a training workload that was
    actually approved in §23's registry, (b) a verified-evaluation result,
    and (c) a specific manifest root -- logged in its own tamper-evident
    log, §21b's construction reused a FIFTH time (§21b, §22's tap
    registry, §23's approval registry, and now this)."""

    def __init__(self, auditor_key: Ed25519PrivateKey, training_registry: ApprovalRegistry):
        self.log = TamperEvidentLog(auditor_key)
        self.training_registry = training_registry

    def release(self, training_cert_hash, training_seed, eval_verification_hash, manifest_root, auditor_id):
        approved, reason = self.training_registry.check(training_cert_hash, training_seed)
        if not approved:
            return False, f"cannot release -- training workload not currently approved ({reason})"
        entry = self.log.append({
            "event": "release",
            "training_cert_hash": training_cert_hash,
            "eval_verification_hash": eval_verification_hash.hex(),
            "manifest_root": manifest_root.hex(),
            "auditor_id": auditor_id,
        })
        return True, entry

    def latest_release_for(self, training_cert_hash):
        latest = None
        for entry in self.log.entries[1:]:
            if entry.payload.get("training_cert_hash") == training_cert_hash:
                latest = entry.payload
        return latest


def receive_and_check(release_record, arrived_shard_bytes_list):
    """What the INFERENCE-ONLY CLUSTER runs before ever deploying anything
    -- independent of the releasing side, over whatever bytes physically
    showed up."""
    if release_record is None:
        return False, "no release record found for this training cert"
    fresh_root, _ = manifest_root_for_shards(arrived_shard_bytes_list)
    if fresh_root.hex() != release_record["manifest_root"]:
        return False, "manifest root mismatch -- received weights do not match the approved release"
    return True, "manifest verified -- matches the approved release exactly"


if __name__ == "__main__":
    print("=" * 92)
    print("1. Full honest chain: approved training workload -> verified eval -> release -> receive")
    print("=" * 92)
    # FIX, per §27: this used to be ONE shared key for both roles below --
    # §27 found that this quietly collapses two logically-distinct
    # authorities (training-workload approval vs. release approval) into a
    # single point of failure, and demonstrated the concrete consequence
    # against this exact file. Two independently generated keys now, so
    # compromising one authority's key doesn't also compromise the other's.
    training_auditor_key = Ed25519PrivateKey.generate()
    release_auditor_key = Ed25519PrivateKey.generate()
    training_registry = ApprovalRegistry(training_auditor_key)
    release_chain = ReleaseChain(release_auditor_key, training_registry)

    training_cert_hash = hashlib.sha256(b"rd_experiment_v1_binary").hexdigest()
    training_seed = training_registry.approve(training_cert_hash, workload_id="rd_experiment_v1", auditor_id="auditor_04")
    print(f"  §23 approval: cert={training_cert_hash[:16]}... seed={training_seed}")

    # Stand-in for 24a's real DiFR-verified eval run: what actually gets
    # bound here is a hash of the eval verification RESULT, not the
    # weights themselves -- any real (avg_deviation, passed) summary from
    # 24a's verified_evals.py would serve identically.
    eval_result_summary = b"eval_suite_v1:avg_deviation=0.0000:passed=True:n_prompts=8"
    eval_verification_hash = hashlib.sha256(eval_result_summary).digest()
    print(f"  24a verified-eval hash: {eval_verification_hash.hex()[:16]}...")

    real_shards = [os.urandom(1024) for _ in range(9)]  # odd count on purpose,
                                                           # exercising the same
                                                           # last-node-duplication
                                                           # path §4's tree tests did
    approved_root, _ = manifest_root_for_shards(real_shards)
    ok, entry = release_chain.release(training_cert_hash, training_seed, eval_verification_hash, approved_root, auditor_id="auditor_09")
    print(f"  Release decision: ok={ok}, manifest_root={approved_root.hex()[:16]}...")
    assert ok

    record = release_chain.latest_release_for(training_cert_hash)
    received_ok, msg = receive_and_check(record, real_shards)
    print(f"  Receiving cluster check (correct shards): ok={received_ok} ({msg})")
    assert received_ok
    print("PASS: full chain verifies end to end.\n")

    print("=" * 92)
    print("2. Release attempted on a training workload that was never approved -- must be rejected")
    print("=" * 92)
    unapproved_cert = hashlib.sha256(b"some_other_workload").hexdigest()
    ok, msg = release_chain.release(unapproved_cert, 0, eval_verification_hash, approved_root, auditor_id="auditor_09")
    print(f"  Release attempt: ok={ok} ({msg})")
    assert not ok
    print("PASS: no release without a live, correctly-seeded §23 approval to point at.\n")

    print("=" * 92)
    print("3. THE ACTUAL ATTACK: weights swapped after release approval, before arrival")
    print("=" * 92)
    tampered_shards = list(real_shards)
    tampered_shards[4] = os.urandom(1024)  # one shard, out of nine, silently swapped
                                             # in transit -- everything else identical
    received_ok, msg = receive_and_check(record, tampered_shards)
    print(f"  Receiving cluster check (1 of 9 shards swapped): ok={received_ok} ({msg})")
    assert not received_ok
    print("PASS: a single swapped shard out of nine changes the root and is caught -- the")
    print("receiving cluster never has to trust the transport, only recompute independently.\n")

    print("=" * 92)
    print("4. Why a MERKLE manifest, not a flat whole-file hash, for something this size")
    print("=" * 92)
    print("A flat hash over the whole weight file already catches case 3 above -- one changed")
    print("byte anywhere changes the hash. What it can't do: at real scale (a 70B-parameter")
    print("model is ~140GB in FP16, per this document's own §19 reference figure), a later")
    print("dispute about ONE specific shard would need re-hashing the entire file to confirm")
    print("anything. A Merkle proof answers the same question in O(log n):")
    idx = 4
    proof = ManifestTree([hashlib.sha256(s).digest() for s in real_shards]).proof(idx)
    leaf = hashlib.sha256(tampered_shards[idx]).digest()  # the SWAPPED shard's hash
    verified = ManifestTree.verify_inclusion(leaf, idx, proof, approved_root)
    print(f"  Checking shard {idx}'s (tampered) hash against the approved root via a "
          f"{len(proof)}-hash proof: verifies={verified} (must be False)")
    assert not verified
    correct_leaf = hashlib.sha256(real_shards[idx]).digest()
    verified_correct = ManifestTree.verify_inclusion(correct_leaf, idx, proof, approved_root)
    print(f"  Same proof, against the ORIGINAL (untampered) shard {idx}: verifies={verified_correct} (must be True)")
    assert verified_correct
    print("PASS: a single shard can be checked against the already-approved root directly,")
    print("without re-hashing the other 8 -- exactly §4's own justification for a tree over a")
    print("flat hash-chain, reapplied here rather than re-argued.\n")

    print("=" * 92)
    print("5. Tampering with the release record itself, after the fact")
    print("=" * 92)
    release_index = len(release_chain.log.entries) - 1
    print(f"  entry {release_index} BEFORE: manifest_root={release_chain.log.entries[release_index].payload['manifest_root'][:16]}...")
    forged_root, _ = manifest_root_for_shards(tampered_shards)  # attacker tries to
                                                                    # retroactively bless
                                                                    # the swapped shards
    release_chain.log.entries[release_index].payload["manifest_root"] = forged_root.hex()
    print(f"  entry {release_index} AFTER:  manifest_root={release_chain.log.entries[release_index].payload['manifest_root'][:16]}...")
    tampered_ok, tampered_msg = release_chain.log.verify_integrity()
    print(f"  Release log integrity check: {tampered_ok} ({tampered_msg})")
    assert not tampered_ok
    print("Caught the same way all four prior reuses of this log caught tampering. This is")
    print("the fifth time §21b's construction has been reused in this document without")
    print("needing modification -- §21b, §22's tap registry, §23's approval registry, this")
    print("file's release log, and (structurally identical) the check in part 3 above.")
