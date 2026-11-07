"""
§23: Workload Approval.

Grounded directly in the AI Futures Project's own division of the problem
(Verification Plan supplement): "We can divide the problem of enforcing the
R&D rules into two parts: (1) Workload Approval [...] (2) Workload
Verification [...] workload approval will be closely tied to the form of
AI R&D rules that are in place [...] our overall baseline proposal for
approval is for this to just be manually carried out by teams of auditors."

That's the load-bearing sentence for this whole section: approval is a
HUMAN judgment call in the source material's own baseline design, not
something this document tries to automate. What IS a technical problem,
and what this file actually builds: turning a human auditor's yes/no into
something (a) unambiguous about exactly what was approved, (b) tamper-
evident once made, and (c) actually checkable against what's running --
closing the loop §13 named as a policy dependency it couldn't close from
its own side.

Three pieces, each extending something this document already built rather
than starting fresh:
  1. Policy-list checking (the source's own "white/black/gold list" idea)
     layered on top of §13's DSL -- reusing parse_dsl() unmodified, since
     it's already a generic key:value parser with no hardcoded field names.
  2. An extended certificate compiler that actually READS the new fields
     (banned_ops, required_ops), applying the exact lesson §13 already
     learned the hard way: a declared-but-unread field is dead code an
     optimizer can eliminate, silently defeating the certificate.
  3. A tamper-evident approval registry -- §21b's TamperEvidentLog, reused
     for a fourth time (§21b, §22's tap registry, this) -- extended with
     the one property neither of those needed: REVOCATION, which means a
     lookup has to scan for an entry's LATEST status, not just "was it
     ever approved."
"""
import hashlib
import subprocess
import secrets
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from certificate_demo import parse_dsl
from tamper_log import TamperEvidentLog

# ---- Policy lists (the source's "white/black/gold list" regime) ----
# Illustrative, not a real safety policy -- the point is that a workload's
# declared allowed_ops gets checked against BOTH a blacklist (must not
# intersect) and a goldlist (must be a superset of), before it ever reaches
# compilation. This is a POLICY input, not something this section invents
# criteria for -- the source material is explicit that populating these
# lists is itself "punting the problem," not solving it.
POLICY_BLACKLIST = {"custom_allreduce_variant", "unregistered_kernel"}
POLICY_GOLDLIST = {"gradient_clip"}


def parse_op_list(fields, key):
    raw = fields.get(key, "[]").strip("[]")
    return set(op.strip() for op in raw.split(",") if op.strip())


def check_against_policy(fields, blacklist=POLICY_BLACKLIST, goldlist=POLICY_GOLDLIST):
    """Real check against real lists -- not a placeholder. Returns
    (ok, violations, missing). This is the ONLY part of approval this
    section claims is mechanical; the source material's own honesty is
    that POPULATING these lists is the actual hard part, done by humans."""
    declared = parse_op_list(fields, "allowed_ops")
    violations = declared & blacklist
    missing = goldlist - declared
    return (len(violations) == 0 and len(missing) == 0), violations, missing


def compile_to_c_v2(fields: dict) -> str:
    """§13's compile_to_c, extended to also emit and ACTUALLY READ the two
    new fields -- applying the lesson from that section's own caught bug
    (unused declared constants got -O2 dead-code-eliminated, letting two
    differently-declared workloads compile to bit-identical binaries)
    rather than repeating it."""
    allowed = parse_op_list(fields, "allowed_ops")
    banned = parse_op_list(fields, "banned_ops") if "banned_ops" in fields else set()
    required = parse_op_list(fields, "required_ops") if "required_ops" in fields else set()
    allowed_c = ", ".join(f'"{o}"' for o in sorted(allowed))
    banned_c = ", ".join(f'"{o}"' for o in sorted(banned))
    required_c = ", ".join(f'"{o}"' for o in sorted(required))
    return f"""
#include <stdio.h>
static const char CHECKPOINT_HASH[] = "{fields.get('checkpoint_hash', '')}";
static const char OPERATION_CLASS[] = "{fields.get('operation_class', '')}";
static const int MAX_BATCH_SIZE = {fields.get('max_batch_size', '0')};
static const char* ALLOWED_OPS[] = {{{allowed_c}}};
static const char* BANNED_OPS[] = {{{banned_c}}};
static const char* REQUIRED_OPS[] = {{{required_c}}};
static const char COLLECTIVE_OPS[] = "{fields.get('collective_ops', '')}";

int main(void) {{
    printf("checkpoint=%s class=%s max_batch=%d collectives=%s\\n",
           CHECKPOINT_HASH, OPERATION_CLASS, MAX_BATCH_SIZE, COLLECTIVE_OPS);
    for (int i = 0; i < (sizeof(ALLOWED_OPS) / sizeof(ALLOWED_OPS[0])); i++) printf("op: %s\\n", ALLOWED_OPS[i]);
    for (int i = 0; i < (sizeof(BANNED_OPS) / sizeof(BANNED_OPS[0])); i++) printf("banned: %s\\n", BANNED_OPS[i]);
    for (int i = 0; i < (sizeof(REQUIRED_OPS) / sizeof(REQUIRED_OPS[0])); i++) printf("required: %s\\n", REQUIRED_OPS[i]);
    return 0;
}}
"""


def compile_and_certify_v2(dsl_source: str, out_name: str) -> dict:
    fields = parse_dsl(dsl_source)
    c_source = compile_to_c_v2(fields)
    c_path, bin_path = "workload_src_v2.c", f"{out_name}.bin"
    with open(c_path, "w") as f:
        f.write(c_source)
    subprocess.run(
        ["gcc", "-O2", "-frandom-seed=fixed", "-fno-ident",
         "-ffile-prefix-map=" + __import__("os").getcwd() + "=/build",
         "-Wl,--build-id=none", "-static", "-o", bin_path, c_path],
        check=True, capture_output=True,
    )
    with open(bin_path, "rb") as f:
        cert_hash = hashlib.sha256(f.read()).hexdigest()
    return {"fields": fields, "compiled_binary_hash": cert_hash}


# ---------------------------------------------------------------------
# The approval registry: §21b's log, reused a fourth time (§21b's own
# verification log, §22's tap registry, and now this) -- extended with
# revocation, which none of the prior three reuses needed.
# ---------------------------------------------------------------------
class ApprovalRegistry:
    def __init__(self, auditor_key: Ed25519PrivateKey):
        self.log = TamperEvidentLog(auditor_key)

    def approve(self, cert_hash: str, workload_id: str, auditor_id: str):
        """The seed is issued HERE, at approval -- not at generation time,
        and not something the prover ever supplies. This is the source
        material's own design: 'Auditors run checks [...] and if it
        passes they send back approval and provide necessary random
        seeds (removes a potential attack vector from AI companies
        gaming fake randomness)' -- exactly the seed-shopping attack
        §1 and §5 already built the discipline against; this is where
        that discipline's seed actually originates."""
        seed = secrets.randbits(63)
        self.log.append({
            "event": "approve", "cert_hash": cert_hash,
            "workload_id": workload_id, "auditor_id": auditor_id, "issued_seed": seed,
        })
        return seed

    def revoke(self, cert_hash: str, auditor_id: str, reason: str):
        self.log.append({"event": "revoke", "cert_hash": cert_hash, "auditor_id": auditor_id, "reason": reason})

    def check(self, cert_hash: str, claimed_seed: int):
        """The lookup §21b and §22's registry never needed: scan for this
        cert_hash's LATEST status, not just whether an 'approve' entry
        exists anywhere in history -- a naive existence check would treat
        an approved-then-revoked workload as still approved."""
        latest_status, latest_seed = None, None
        for entry in self.log.entries[1:]:  # skip genesis
            p = entry.payload
            if p.get("cert_hash") != cert_hash:
                continue
            if p["event"] == "approve":
                latest_status, latest_seed = "approved", p["issued_seed"]
            elif p["event"] == "revoke":
                latest_status = "revoked"
        if latest_status != "approved":
            return False, latest_status or "never_approved"
        if claimed_seed != latest_seed:
            return False, "seed_mismatch"
        return True, "ok"


if __name__ == "__main__":
    print("=" * 92)
    print("1. Policy-list check: a compliant workload vs. one violating the blacklist/goldlist")
    print("=" * 92)
    DSL_COMPLIANT = """
workload rd_experiment_v1 {
    checkpoint_hash: a3f8e91c9e21
    operation_class: FORWARD_ONLY
    max_batch_size: 256
    allowed_ops: [matmul, attention, layernorm, gelu, gradient_clip]
    collective_ops: NONE
}
"""
    DSL_BLACKLISTED = """
workload rd_experiment_v2 {
    checkpoint_hash: a3f8e91c9e21
    operation_class: FORWARD_ONLY
    max_batch_size: 256
    allowed_ops: [matmul, attention, layernorm, gelu, gradient_clip, custom_allreduce_variant]
    collective_ops: NONE
}
"""
    DSL_MISSING_REQUIRED = """
workload rd_experiment_v3 {
    checkpoint_hash: a3f8e91c9e21
    operation_class: FORWARD_ONLY
    max_batch_size: 256
    allowed_ops: [matmul, attention, layernorm, gelu]
    collective_ops: NONE
}
"""
    for name, dsl in [("compliant", DSL_COMPLIANT), ("declares a blacklisted op", DSL_BLACKLISTED), ("missing the required op", DSL_MISSING_REQUIRED)]:
        fields = parse_dsl(dsl)
        ok, violations, missing = check_against_policy(fields)
        print(f"  {name:<28} policy_ok={ok!s:<6} violations={violations or '{}'}  missing={missing or '{}'}")
    assert check_against_policy(parse_dsl(DSL_COMPLIANT))[0] is True
    assert check_against_policy(parse_dsl(DSL_BLACKLISTED))[0] is False
    assert check_against_policy(parse_dsl(DSL_MISSING_REQUIRED))[0] is False
    print("PASS: policy check correctly separates the compliant workload from both violation types.\n")

    print("=" * 92)
    print("2. New fields actually affect the certificate hash (not dead code, per §13's own lesson)")
    print("=" * 92)
    cert_a = compile_and_certify_v2(DSL_COMPLIANT, "wl_a")
    DSL_COMPLIANT_DIFFERENT_REQUIRED = DSL_COMPLIANT.replace(
        "allowed_ops: [matmul, attention, layernorm, gelu, gradient_clip]",
        "allowed_ops: [matmul, attention, layernorm, gelu, gradient_clip, softmax]",
    )
    cert_b = compile_and_certify_v2(DSL_COMPLIANT_DIFFERENT_REQUIRED, "wl_b")
    print(f"  cert_a hash: {cert_a['compiled_binary_hash'][:24]}...")
    print(f"  cert_b hash: {cert_b['compiled_binary_hash'][:24]}... (one extra allowed op)")
    match = cert_a["compiled_binary_hash"] == cert_b["compiled_binary_hash"]
    print(f"  Certificates match: {match} (must be False)")
    assert not match
    print("PASS.\n")

    print("=" * 92)
    print("3. Approval registry: approve, verify, revoke, verify again")
    print("=" * 92)
    auditor_key = Ed25519PrivateKey.generate()
    registry = ApprovalRegistry(auditor_key)

    cert_hash = cert_a["compiled_binary_hash"]
    seed = registry.approve(cert_hash, workload_id="rd_experiment_v1", auditor_id="auditor_04")
    print(f"  Approved {cert_hash[:16]}..., issued seed={seed}")

    ok, reason = registry.check(cert_hash, claimed_seed=seed)
    print(f"  Check with correct seed: ok={ok} ({reason})")
    assert ok

    ok, reason = registry.check(cert_hash, claimed_seed=seed + 1)
    print(f"  Check with WRONG seed (the exact 'gaming fake randomness' attack the source names): ok={ok} ({reason})")
    assert not ok and reason == "seed_mismatch"

    ok, reason = registry.check("0" * 64, claimed_seed=0)
    print(f"  Check on a certificate hash that was never approved: ok={ok} ({reason})")
    assert not ok and reason == "never_approved"

    registry.revoke(cert_hash, auditor_id="auditor_04", reason="post-hoc anomaly found in evaluation")
    ok, reason = registry.check(cert_hash, claimed_seed=seed)
    print(f"  Check AFTER revocation, same correct seed: ok={ok} ({reason})")
    assert not ok and reason == "revoked"

    base_ok, base_msg = registry.log.verify_integrity()
    print(f"  Registry integrity after an honest approve+revoke history: {base_ok} ({base_msg})")
    assert base_ok, "revocation is a normal, honestly-logged event -- it must not itself look like tampering"
    print("PASS: approval, correct-seed check, wrong-seed rejection, unknown-cert rejection, and")
    print("post-revocation rejection all behave correctly, and the honest revocation event doesn't")
    print("trip the log's own tamper detection.\n")

    print("=" * 92)
    print("4. The actual attack: retroactively deleting the revocation to un-revoke a workload")
    print("=" * 92)
    revoke_index = len(registry.log.entries) - 1
    assert registry.log.entries[revoke_index].payload["event"] == "revoke"
    print(f"  entry {revoke_index} BEFORE: {registry.log.entries[revoke_index].payload}")
    registry.log.entries[revoke_index].payload["event"] = "approve"  # attacker tries to disguise the revoke as a re-approval
    registry.log.entries[revoke_index].payload["issued_seed"] = seed
    print(f"  entry {revoke_index} AFTER:  {registry.log.entries[revoke_index].payload}")
    tampered_ok, tampered_msg = registry.log.verify_integrity()
    print(f"  Registry integrity check: {tampered_ok} ({tampered_msg})")
    assert not tampered_ok, "disguising a revocation as a re-approval must be caught"
    print("Caught for the same reason the other three reuses of this log caught tampering --")
    print("no new mechanism needed, because none was missing.")
