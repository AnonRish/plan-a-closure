import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from hardware.attestation import *
def test_attestation_signature_and_measurements():
    key=Ed25519PrivateKey.generate()
    pub=base64.b64encode(key.public_key().public_bytes_raw()).decode()
    q0=AttestationQuote("d","boot","firm","p","n","")
    sig=base64.b64encode(key.sign(quote_payload(q0))).decode()
    q=AttestationQuote("d","boot","firm","p","n",sig)
    assert verify_attestation(q,pub,"boot","firm","p","n")["status"]=="PASS"
def test_attestation_rejects_nonce_replay():
    key=Ed25519PrivateKey.generate()
    pub=base64.b64encode(key.public_key().public_bytes_raw()).decode()
    q0=AttestationQuote("d","boot","firm","p","n","")
    sig=base64.b64encode(key.sign(quote_payload(q0))).decode()
    q=AttestationQuote("d","boot","firm","p","n",sig)
    assert verify_attestation(q,pub,"boot","firm","p","other")["status"]=="FAIL"
