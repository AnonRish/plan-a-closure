"""
§21b: append-only, hash-chained, signed verification log.

Real Ed25519 signing via the `cryptography` library (already used in §15 —
consistent choice, and an audited implementation rather than a hand-rolled
one). Worth being explicit about why hand-rolling gets avoided here
specifically: a separate document shared with me implemented "512-bit RSA"
by hand for this exact purpose, and independently checking it (this
document's own habit throughout) found the modulus was actually 79 bits,
p*q didn't equal the stated n, and e*d wasn't a valid inverse pair under
the stated modulus at all — the shown "execution output" didn't match what
the code produced when actually run. Nothing about that is a reason to
avoid a hash-chained log; it's a reason not to hand-roll the signature
scheme underneath one.
"""
import json
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature


class LogEntry:
    def __init__(self, index, prev_hash, payload):
        self.index = index
        self.prev_hash = prev_hash
        self.payload = payload
        self.signature = None

    def entry_hash(self):
        serialized = json.dumps(
            {"index": self.index, "prev_hash": self.prev_hash, "payload": self.payload},
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def sign(self, private_key):
        self.signature = private_key.sign(bytes.fromhex(self.entry_hash()))

    def verify(self, public_key):
        if self.signature is None:
            return False
        try:
            public_key.verify(self.signature, bytes.fromhex(self.entry_hash()))
            return True
        except InvalidSignature:
            return False


class TamperEvidentLog:
    def __init__(self, private_key):
        self.private_key = private_key
        self.public_key = private_key.public_key()
        self.entries = []
        genesis = LogEntry(0, "0" * 64, {"event": "genesis"})
        genesis.sign(self.private_key)
        self.entries.append(genesis)

    def append(self, payload):
        prev_hash = self.entries[-1].entry_hash()
        entry = LogEntry(len(self.entries), prev_hash, payload)
        entry.sign(self.private_key)
        self.entries.append(entry)
        return entry

    def verify_integrity(self):
        for i in range(1, len(self.entries)):
            current, previous = self.entries[i], self.entries[i - 1]
            expected_prev = previous.entry_hash()
            if current.prev_hash != expected_prev:
                return False, f"hash-chain broken at entry {i}: expected prev_hash {expected_prev[:12]}..., got {current.prev_hash[:12]}..."
            if not current.verify(self.public_key):
                return False, f"signature invalid at entry {i}"
        return True, f"all {len(self.entries)} entries verified (hash chain + signature)"


if __name__ == "__main__":
    priv = Ed25519PrivateKey.generate()
    log = TamperEvidentLog(priv)

    print("=" * 90)
    print("Building a real log: 5 verification reports, real Ed25519 signatures")
    print("=" * 90)
    for i in range(5):
        log.append({"session_id": f"sess_{100+i}", "avg_deviation": round(0.01 * i, 3), "passed": i != 2})

    ok, msg = log.verify_integrity()
    print(f"Baseline check: {ok} ({msg})")
    assert ok, "a freshly built, untampered log must verify — if this fails, the implementation is broken"

    print()
    print("=" * 90)
    print("Tampering with entry 3's payload (session sess_102, the one honest FAIL in the log,")
    print("now placed mid-log so both the direct signature check AND downstream chain-breakage")
    print("can be demonstrated in one test — a first pass at this test put the only FAIL at the")
    print("very end of the log, where there's no downstream entry to show breaking)")
    print("=" * 90)
    print(f"entry 3 payload BEFORE: {log.entries[3].payload}")
    log.entries[3].payload["passed"] = True  # was False — flipping a real failure to a fake pass
    print(f"entry 3 payload AFTER:  {log.entries[3].payload}")
    ok, msg = log.verify_integrity()
    print(f"Post-tamper check: {ok} ({msg})")
    assert not ok, "tampering MUST be caught — if this passes, the log provides no real guarantee"

    print()
    print("=" * 90)
    print("Confirming the failure is caught at BOTH the signature check (payload changed) AND")
    print("downstream chain breakage (entry 4's stored prev_hash no longer matches entry 3's")
    print("now-changed hash) — both properties hold, not just one")
    print("=" * 90)
    entry3_sig_valid = log.entries[3].verify(log.public_key)
    entry4_chain_valid = log.entries[4].prev_hash == log.entries[3].entry_hash()
    print(f"entry 3 signature still valid against its (now-changed) content: {entry3_sig_valid} (must be False)")
    print(f"entry 4's stored prev_hash still matches entry 3's (now-changed) hash: {entry4_chain_valid} (must be False)")
    assert not entry3_sig_valid
    assert not entry4_chain_valid

    print()
    print("=" * 90)
    print("Confirming a signature genuinely can't be forged without the private key")
    print("(re-sign entry 3 with a DIFFERENT, attacker-generated key -- simulating an attacker who")
    print(" edited the payload and tried to cover it by re-signing with their own key)")
    print("=" * 90)
    attacker_key = Ed25519PrivateKey.generate()
    log.entries[3].sign(attacker_key)  # attacker re-signs with THEIR key, not the real one
    forged_valid = log.entries[3].verify(log.public_key)  # verifier checks against the REAL public key
    print(f"Forged signature (attacker's own key) verifies against the real server's public key: {forged_valid} (must be False)")
    assert not forged_valid
    print()
    print("All required properties demonstrated: tampering breaks both hash-chain and signature")
    print("checks, and forging a replacement signature without the real private key fails too.")
