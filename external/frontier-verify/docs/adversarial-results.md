# Adversarial Results

Assume the prover is extremely capable and dishonest, per the brief's own
framing. For each of the 15 named attacks: what it requires, whether this
repository detects it TODAY, what evidence a test uses if one exists, and
residual risk. "Detected" here always means "this repository's code
demonstrably behaves correctly against this specific attack, right now" --
never "this attack is impossible" or "this attack has been made
uneconomical," which are much stronger claims this document does not make.

| # | Attack | Requires | Detected? | Evidence | Residual risk |
|---|---|---|---|---|---|
| 1 | Forged evidence (fabricate a whole Evidence bundle) | Nothing -- evidence is self-reported | **NO** for the content; **YES** for post-issuance tampering with a receipt referencing it | `tests/security/test_receipt_tamper.py` (5 tamper vectors) | The content of ANY evidence bundle is untrusted by construction until real hardware attestation exists (`docs/threat-model.md`, Q.A) |
| 2 | Replay (resubmit a captured valid submission) | Network access to a prior valid submission | **PARTIAL** | `tests/unit/test_policy_evaluator.py::test_stale_evidence_rejected` (freshness window only) | No nonce/challenge-response; a replay within the freshness window succeeds. See `docs/threat-model.md`, Q.D |
| 3 | Workload substitution (claim workload A, actually ran B) | Control of the prover's own machine | **NO** | -- | Needs independent recomputation (Phase 6, NOT_IMPLEMENTED) or network evidence (NOT_IMPLEMENTED) |
| 4 | Model substitution (claim model A, actually served B) | Control of the prover's own machine | **NO** | -- | `ModelIdentity` is entirely self-reported; needs real weights-digest verification tied to attestation |
| 5 | Runtime substitution (claim engine/config A, actually ran B) | Control of the prover's own machine | **NO** | -- | Same as #4, for `RuntimeIdentity` |
| 6 | Selective/partial reporting -- resubmit the SAME evidence_id with DIFFERENT content | API access | **YES** (Phase 2 fix) | `tests/adversarial/test_selective_evidence.py::test_evidence_id_resubmitted_with_different_content_is_rejected` -- returns 409, original content unchanged | Only catches the "same id, different content" shape of this attack. Simply never submitting evidence for an unwanted workload is a DIFFERENT attack -- see #8 |
| 7 | Timestamp manipulation | Control of the prover's own clock | **NO** | -- | `Evidence.created_at` is self-reported; freshness checks (#2) are defeated by a prover that lies about its own clock. See `docs/threat-model.md`, Q.I |
| 8 | Evidence withholding (never submit evidence for a workload) | Control of the prover's own infrastructure | **NO** | -- | Nothing observes the prover independently of what it chooses to submit -- this is the same gap network evidence exists to close, and network evidence is NOT_IMPLEMENTED |
| 9 | Verifier compromise (attacker gains control of the verifier process) | Compromise of verifier infrastructure | **NO** | -- | A compromised verifier can sign arbitrary false receipts; nothing detects this after the fact. No anomaly detection, no multi-party signing |
| 10 | Key compromise (attacker obtains the verifier's private key without compromising the process) | Exfiltration of key material (easy against `LocalFileKeyProvider`'s plaintext-on-disk storage -- see `docs/protocol/key-management.md`) | **NO** | -- | Rotation exists (`tests/integration/test_api_end_to_end.py::test_receipt_survives_key_rotation`) but rotation is a HYGIENE mechanism, not a REVOCATION mechanism -- there is no way to mark a specific key_id as "compromised, distrust retroactively" versus "rotated out, still trustworthy for old receipts." Both look identical today |
| 11 | Sampled-workload gaming (predict which chunks will be recomputation-sampled, only falsify the rest) | Predictive insight into the verifier's sampling | **N/A** | -- | Recomputation itself is NOT_IMPLEMENTED (Phase 6). See `docs/research/recomputation.md` for the commit-reveal design intended to address this specific attack once recomputation exists, and its own honestly-stated limits |
| 12 | Hidden computation (run undeclared workloads alongside declared ones) | Control of the prover's datacenter | **NO** | -- | Needs network evidence / side-channel work, both NOT_IMPLEMENTED. See `docs/research/hidden-computation.md` |
| 13 | Fake recomputation (submit a plausible-looking but fabricated recomputation result) | -- | **N/A** | -- | Recomputation NOT_IMPLEMENTED; nothing to attack yet |
| 14 | Malicious storage (tamper with evidence bytes after they're stored) | Write access to the storage backend | **YES**, for corruption/tampering detection after the fact | `tests/conformance/test_content_addressed.py::test_corrupted_stored_bytes_are_detected_on_read` -- directly corrupts a stored file, confirms `IntegrityError` on read | Detects tampering; does NOT prevent an attacker with storage write access from a consistent substitution at write time (i.e., replacing content AND correctly rehashing it before anyone reads it back is a different, undetectable attack against this specific mechanism) |
| 15 | Compromised management plane (attacker controls the process orchestrating the verifier, not the verifier itself) | Infrastructure compromise one level up | **NO** | -- | No separation of duties anywhere in this design; a single compromised host running the verifier process compromises everything the verifier can do, including rotating keys to attacker-controlled ones |

## Phase 3: the eight named attacks against commit-reveal recomputation

Section 17 of the Phase 3 brief named eight specific attacks against the
recomputation system (`frontier_verify/recomputation/`) and explicitly
warned against "implement random sampling and call it secure." Scored
honestly, the same way as the table above:

| # | Attack | Testable without real ML inference? | Result |
|---|---|---|---|
| 1 | Predict the challenge | Yes | **Prevented.** `tests/conformance/test_recomputation_sampling.py` shows a naive sampler is perfectly predictable by a prover with zero access to verifier secrets, and commit-reveal sampling is not -- falsifiable, not asserted |
| 2 | Selectively prepare only challenged work | Yes | **Prevented**, via a connection to an existing mechanism, not new recomputation logic: evidence-id collision rejection (Phase 2) means a prover cannot revise its claims after learning the sample -- `tests/adversarial/recomputation/test_attack_commit_reveal.py::test_evidence_immutability_prevents_updating_claims_after_the_challenge_is_known` |
| 3 | Generate a second clean execution for verification | No -- requires binding claimed outputs to actually-served outputs, which needs serving-layer integration not designed yet | **Not addressed.** Genuinely important, honestly unresolved: nothing currently confirms a claimed output was ever actually shown to a real user, as opposed to computed cleanly just for the recomputation check |
| 4 | Omit unchallenged work entirely | Yes | **Not prevented, demonstrated explicitly.** `test_a_never_submitted_chunk_is_invisible_to_recomputation_entirely` shows a chunk that's never submitted is invisible to the whole mechanism -- restates attack #8 above (evidence withholding), for recomputation specifically |
| 5 | Manipulate replay inputs | Yes, after Phase 3's fix | **Prevented**, but only after fixing a real design flaw this adversarial pass found: `recompute_fn` used to take a bare digest (couldn't represent real recomputation at all -- a hash can't be inverted). Now retrieves real content via `ContentAddressedStore`; tampering with stored input is caught by the same integrity mechanism as attack #14 above -- `test_tampering_with_stored_input_after_the_fact_is_caught_not_silently_replayed` |
| 6 | Exploit nondeterminism | No -- the toy `recompute_fn` is deterministic by construction | **Out of scope for this module.** Real ML nondeterminism (floating-point, distributed execution ordering) belongs in `docs/research/real-recomputation.md`'s staged roadmap, not this toy simulation |
| 7 | Exploit numerical tolerance | No -- digest equality has no tolerance concept | **Not applicable to the current design**, but a real finding for future work: if real recomputation ever compares raw floating-point outputs instead of digests, the tolerance window itself becomes new attack surface -- noted in `docs/research/real-recomputation.md`, not solved |
| 8 | Manipulate the verifier's reference implementation | No -- restates an already-tracked risk | **Same category as attacks #9/#15 above** (verifier/management-plane compromise) -- not a new finding specific to recomputation |

Four of eight were genuinely testable and tested. The exercise also
produced a real code fix (attack #5), not just a table -- the strongest
evidence this pass was a genuine attack attempt, not a checklist filled
in optimistically.

## Phase 3: authorization and revocation

Not new attacks against existing mechanisms -- new mechanisms, tested
against their own claimed properties directly:

- **Role restriction genuinely holds**: `tests/unit/test_authorization.py`
  (12 tests) confirms each of the four roles CANNOT do what it shouldn't,
  not merely that authentication exists. The one role separation that
  maps to an actual attack (`PROVER` writing its own `POLICY_AUTHORITY`
  policy) is directly tested, not just documented.
- **Revocation vs. rotation genuinely diverges**: a receipt signed by a
  since-revoked key stays `signature_valid=True` (the cryptographic fact
  never changes) while `currently_trusted` flips to `False` --
  `tests/integration/test_api_end_to_end.py::test_revoked_key_receipt_stays_cryptographically_valid_but_becomes_untrusted`
  exercises the full revoke-then-check-then-rotate-then-recover cycle
  through the live API, not just the `KeyProvider` in isolation.
- **A revoked key structurally cannot sign anything new**:
  `RevokedKeyError` in `frontier_verify/keys/local_provider.py`, tested in
  `tests/unit/test_key_revocation.py`.

Every "YES" in this table protects **integrity of something already
recorded** (a receipt's signature, stored evidence bytes, a specific
evidence_id's content). Every "NO" is about **truthfulness of what gets
recorded in the first place**, or **detecting silence** (something that
was never recorded at all). This is not a coincidence -- it is exactly
what Phase 1's honest ceiling of "L1: tamper-evident record-keeping of
self-reported claims" predicts, and Phase 2 has not moved that ceiling. It
will move once real hardware attestation, recomputation, or network
evidence land -- none of which happened this phase, and none of which are
claimed to have happened.
