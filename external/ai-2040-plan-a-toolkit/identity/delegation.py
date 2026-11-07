from dataclasses import dataclass
import hashlib,json
@dataclass(frozen=True)
class Delegation:
    delegator:str; delegate:str; scope:str; nonce:str; signature_digest:str
    def statement_digest(self):
        x=json.dumps({"delegator":self.delegator,"delegate":self.delegate,"scope":self.scope,"nonce":self.nonce},sort_keys=True,separators=(",",":"))
        return hashlib.sha256(x.encode()).hexdigest()
def expected_signature_digest(d): return hashlib.sha256((d.statement_digest()+"|"+d.delegator).encode()).hexdigest()
def validate_chain(chain,subject):
    if not chain:return {"status":"UNKNOWN","reason":"empty chain"}
    expected=subject; errors=[]; seen_delegators=set()
    for d in reversed(chain):
        if d.delegate!=expected: errors.append("delegate mismatch")
        if d.signature_digest!=expected_signature_digest(d): errors.append("bad signature")
        if d.delegator in seen_delegators: errors.append("delegation cycle")
        seen_delegators.add(d.delegator); expected=d.delegator
    return {"status":"PASS" if not errors else "FAIL","errors":errors,"root_actor":expected}
