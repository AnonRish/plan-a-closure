from __future__ import annotations
from dataclasses import dataclass
import base64, json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

@dataclass(frozen=True)
class AttestationQuote:
    device_id:str
    boot_measurement:str
    firmware_measurement:str
    policy_digest:str
    nonce:str
    signature_b64:str

def quote_payload(q:AttestationQuote)->bytes:
    return json.dumps({"device_id":q.device_id,"boot_measurement":q.boot_measurement,"firmware_measurement":q.firmware_measurement,"policy_digest":q.policy_digest,"nonce":q.nonce},sort_keys=True,separators=(",",":")).encode()

def verify_attestation(q:AttestationQuote,public_key_b64:str,expected_boot:str,expected_firmware:str,expected_policy:str,expected_nonce:str)->dict:
    checks={"boot_measurement":q.boot_measurement==expected_boot,"firmware_measurement":q.firmware_measurement==expected_firmware,"policy_digest":q.policy_digest==expected_policy,"nonce":q.nonce==expected_nonce}
    try:
        key=Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64)); key.verify(base64.b64decode(q.signature_b64),quote_payload(q)); checks["signature"]=True
    except Exception: checks["signature"]=False
    return {"status":"PASS" if all(checks.values()) else "FAIL","checks":checks}
