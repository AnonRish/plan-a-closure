# Verification receipt schema

The other tractable open problem from the AI Security Forum list: "binding verification
to governance" — mapping technical artifacts to legal and treaty instruments, with
schemas, retention rules, and dispute resolution, not just internal consistency.

`trust_composition/` answers *whether* an architecture's independence claim holds.
This answers what the architecture has to hand a court, a treaty secretariat, or an
auditor who wasn't in the room, for a verification decision to be worth anything to
them. A tamper-evident log that only your own software can interpret isn't evidence
to anyone outside your organization; a receipt against a fixed, versioned schema is.

## What's in a receipt

Six required blocks: `subject` (what this is about), `claim` (the assertion, in
plain language, with a stated basis), `evidence_chain` (the hash link — same
tamper-evidence primitive as Arbiter's ledger), `attestation` (who signed, against
what quorum), `governance_binding` (which instrument this is issued under, how long
it must remain checkable, how to dispute it), plus versioning and an optional
free-text producer note.

## Two levels of "valid"

- **Well-formed**: matches the JSON Schema — right fields, right types, right shape.
- **Consummated**: well-formed *and* the quorum was actually met by distinct
  signers. A receipt honestly recording a proposal that's collected 2 of 3 required
  signatures is well-formed — it's just not evidence of anything yet. `validate()`
  returns both, deliberately, rather than collapsing them into one boolean.

The validator also catches the exact failure mode the trust-composition tool found
in Arbiter's original design: a `single-signer` scheme paired with a `required_quorum`
above 1 is flagged explicitly, citing `min_attack=1` — a receipt can't paper over an
unattested single point of failure by asserting a threshold it never actually enforced.

## Running it

```
pip install jsonschema pytest
python3 examples.py              # 1 valid + 4 deliberately broken receipts, printed
python3 -m pytest test_validator.py -v   # 11 tests
```

## What this does not do

It doesn't make a receipt TRUE — a well-formed, fully-quorum-signed receipt asserting
something false is still well-formed and consummated; this schema constrains the
*shape* of an attestation, not the accuracy of what's attested. And `instrument_ref`
/ `dispute_process` here are free-text placeholders — wiring this to an actual treaty
or legal process is a policy and legal-drafting problem, not a schema-design one.
