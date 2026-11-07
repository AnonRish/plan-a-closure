from challenge_scheduler.scheduler import *
def test_joint_challenge_binds_both_reveals():
    vc,vr=random_commitment("verifier"); pc,pr=random_commitment("prover")
    t=ChallengeTranscript(vc,pc,vr,pr,"claim")
    assert len(derive_joint_challenge(t))==64
def test_tampered_reveal_is_rejected():
    vc,vr=random_commitment("verifier"); pc,pr=random_commitment("prover")
    t=ChallengeTranscript(vc,pc,vr+"x",pr,"claim")
    try: derive_joint_challenge(t)
    except ValueError: pass
    else: assert False
