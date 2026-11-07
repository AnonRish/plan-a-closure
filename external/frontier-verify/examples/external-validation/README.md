# External Validation Package

Five real, pre-generated, signed receipts — no source modification needed
to try any of this. Each behavior below was actually run and confirmed
before this package was committed (`tests/conformance/test_external_validation_fixtures.py`
pins them as a permanent regression check, so they'll keep matching this
description as the codebase evolves).

| File | What it is | Expected result |
|---|---|---|
| `01_valid_receipt.json` | A genuine, correctly signed receipt | **PASS** |
| `02_tampered_result.json` | Same receipt, `result` field flipped after signing | **FAIL** |
| `03_tampered_assurance_level.json` | Same receipt, `assurance_level` changed to `L5` after signing | **FAIL** |
| `04_corrupted_signature.json` | Same receipt, signature bytes replaced with garbage | **FAIL** |
| `01_valid_receipt.json` + `wrong_public_key.txt` | The genuinely valid receipt, checked against the WRONG public key | **FAIL** |

## Try it yourself

No installation beyond `pip install cryptography` (Python) or nothing at
all (Node — uses only the standard library plus built-in `crypto`):

```bash
PUBKEY=$(cat verifier_public_key.txt)

python3 ../../tools/standalone-verifier/verify_receipt.py 01_valid_receipt.json "$PUBKEY"
# signature_valid=True

python3 ../../tools/standalone-verifier/verify_receipt.py 02_tampered_result.json "$PUBKEY"
# signature_valid=False

node ../../tools/standalone-verifier/verify_receipt.js 01_valid_receipt.json "$PUBKEY"
# signature_valid=true -- same answer, completely different implementation
```

Try `01_valid_receipt.json` against `wrong_public_key.txt` instead of
`verifier_public_key.txt` — it fails, even though the receipt itself is
completely genuine, because it's the wrong key.

## What this package proves, and what it doesn't

**Proves**: this project's specific claim that a receipt is tamper-evident
and independently checkable without installing the reference
implementation is real and reproducible outside the development
environment it was built in — you don't have to take the test suite's
word for it.

**Does not prove**: anything about hardware attestation, real
recomputation, or whether any evidence a receipt might reference was ever
truthful. See `docs/threat-model.md` before drawing broader conclusions
from five JSON files verifying correctly.

## Everything else in this repository, without modifying source

- `tests/conformance/` — runnable directly: `pytest tests/conformance/ -v`
- `examples/integration/generic_python_service/` — a real, tested async
  integration pattern you can adapt without touching `frontier_verify/`
  internals.
- `docs/reviews/external-review.md` — if you're the "external person"
  this package is for, that document has a structured starting point for
  going further than these five files.
