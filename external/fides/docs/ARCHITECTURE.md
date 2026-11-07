# Architecture: one epoch, start to finish

The README diagram shows the static shape of the system. This is the same thing as a sequence over time, for a single epoch — useful for seeing exactly when each cryptographic guarantee kicks in.

```mermaid
sequenceDiagram
    participant D as Device (accelerator)
    participant P as Prover (tap)
    participant Reg as Registry
    participant V as Verifier
    participant L as AuditLedger

    D->>P: kernel events (op, timing, bytes)
    P->>P: extract() features, classify() workload
    P->>P: build BLAKE3 Merkle tree, root = merkle_root(leaves)
    P->>P: sign(root + declared_class + epoch_id)
    P->>Reg: publish Commitment(root, declared_class, signature, pubkey)
    Note over Reg: commitment is now public.<br/>Prover cannot retroactively change it.

    V->>V: choose_sample(n_events) -- seeded on V's side only
    V->>P: request reveal(epoch_id, sampled_indices)
    Note over P,V: indices were chosen after commitment,<br/>so P could not have hidden bad events<br/>from this specific sample in advance.
    P->>V: reveal (leaf bytes, Merkle proof) for each sampled index

    V->>V: verify_signature(...)
    V->>V: for each revealed leaf: verify(leaf, proof, root)
    V->>V: if declared "inference": check no revealed leaf<br/>decodes to a backward/optimizer op
    V->>L: append(device_id, AuditResult)
    L->>L: entry_hash = BLAKE3(prev_hash || result fields)
    L->>L: sign(entry_hash)
    Note over L: any later edit to this entry changes its<br/>recomputed hash, breaking the chain from<br/>here forward -- checkable by anyone holding<br/>an earlier copy of entry_hash.
```

## Why the ordering matters

The two "Note" boxes above are the two load-bearing security properties, and both come from *ordering*, not from any single cryptographic primitive being unbreakable:

1. **Commit before sample.** The verifier's sampling indices are chosen after the root is already published. A prover trying to hide bad events would need to know in advance which indices get checked — but that choice hasn't been made yet when the commitment goes out.
2. **Hash-chain before publish, not after.** The ledger's tamper-evidence only holds if `entry_hash` reaches at least one party outside the auditor's control at the time the entry is created. `verify_chain()` run later against a *held-back* copy the auditor never let anyone see would not catch anything — this repo doesn't model an external publication step, and a real deployment would need one (see `spec/PROTOCOL.md` section 6).

## Module dependency graph

```mermaid
flowchart TD
    trace[trace.py] --> features[features.py]
    features --> classifier[classifier.py]
    trace --> commitment[commitment.py]
    commitment --> attestation[attestation.py]
    classifier --> attestation
    identity[identity.py] --> attestation
    attestation --> ledger[ledger.py]
    identity --> ledger
    attestation --> protocol[protocol.py]
    ledger --> protocol
```

No module reaches back up the chain — `trace.py` and `identity.py` know nothing about the rest of the system, which is what makes it possible to swap `trace.py` for a real profiler-backed source (spec section 7) without touching the commitment, attestation, or ledger logic at all.
