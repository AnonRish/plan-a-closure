
from crypto.proof_envelope import *
def test_proof_envelope_requires_statement_and_verifier():
    e=ProofEnvelope("s","stark","p","v"); assert validate_envelope(e)["status"]=="PASS"
def test_statement_id_is_deterministic():
    assert statement_id("model","input","output")==statement_id("model","input","output")
