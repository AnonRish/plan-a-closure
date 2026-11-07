# Standalone Receipt Verifier

A single file, `verify_receipt.py`, that checks a Frontier Verify receipt's
Ed25519 signature with **no dependency on the `frontier_verify` package** --
only the Python standard library plus `cryptography`.

```bash
pip install cryptography
python3 verify_receipt.py receipt.json <verifier_public_key_hex>
```

Get the public key from the verifier that issued the receipt: either
`GET /v1/verifier/public-key/{key_id}` (using the `verifier_key_id` field
from the receipt itself, since keys rotate -- see
`../../docs/protocol/key-management.md`) or an out-of-band channel you
trust more than that endpoint.

## Why this exists as a separate file, not a CLI flag

`fv receipt verify` (the main CLI) does the same offline check, but it's
part of the `frontier_verify` package -- installing it means installing
FastAPI, pydantic, typer, httpx, and everything else this repo depends on.
This file exists to make the much stronger claim literal: a relying party
who has never heard of the rest of this repository, and never will, can
still get a correct answer about whether a receipt is genuine. That's the
actual meaning of "independently verifiable" in
`docs/receipt-specification.md` -- not a slogan, a ~90-line file anyone can
audit end to end in a few minutes.

`tests/conformance/test_standalone_verifier_agrees.py` cross-checks this
file's `verify_receipt()` against the main package's
`frontier_verify.receipts.signing.verify_receipt()` on identical inputs,
on every test run. If they ever disagree, that test fails -- which is the
point of having two independent implementations of the same check.
