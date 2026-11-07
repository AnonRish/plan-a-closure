from __future__ import annotations
from dataclasses import dataclass
import hashlib,hmac,secrets

@dataclass(frozen=True)
class ChallengeCommitment:
    party_id:str
    commitment:str

@dataclass(frozen=True)
class ChallengeTranscript:
    verifier_commitment:ChallengeCommitment
    prover_commitment:ChallengeCommitment
    verifier_reveal:str
    prover_reveal:str
    claim_root:str

def commit_entropy(party_id:str,entropy:str)->ChallengeCommitment:
    return ChallengeCommitment(party_id,hashlib.sha256((party_id+"|"+entropy).encode()).hexdigest())

def derive_joint_challenge(t:ChallengeTranscript)->str:
    for c,r in ((t.verifier_commitment,t.verifier_reveal),(t.prover_commitment,t.prover_reveal)):
        if not hmac.compare_digest(c.commitment,hashlib.sha256((c.party_id+"|"+r).encode()).hexdigest()):
            raise ValueError("entropy reveal does not match commitment")
    return hashlib.sha256("|".join((t.claim_root,t.verifier_reveal,t.prover_reveal)).encode()).hexdigest()

def random_commitment(party_id:str):
    entropy=secrets.token_hex(32)
    return commit_entropy(party_id,entropy),entropy
