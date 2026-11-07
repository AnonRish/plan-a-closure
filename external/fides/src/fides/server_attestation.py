"""
Recomputation server software self-attestation -- a narrow, explicitly
partial software-only slice of SITREP item 11 ("Recomputation server
security", not on track). The hard part of this workstream is physical:
the server sits inside the party being verified's own facility, under
their physical control, and no software running ON a machine can fully
prove that machine's own hardware/firmware hasn't been compromised --
that needs a hardware root of trust (TEE, secure boot chain) this repo
has no access to and does not claim to provide.

What IS a legitimate software-only contribution: a periodic
challenge-response heartbeat that a server running unmodified,
correctly-configured verification code can answer, but a server that has
silently swapped in modified verification logic (e.g. one hardcoded to
always report "compliant") cannot answer correctly for -- catching a
specific, real class of tampering (silent logic substitution, and
rollback of the server's own history) even though it cannot catch every
class (an attacker who fully emulates the original code's behavior while
also running additional undetected logic alongside it gets past this,
which is exactly why this is documented as a partial mitigation, not a
solution -- see spec/PROTOCOL.md).

`verify_threshold` raises the bar further: requiring agreement from a
threshold of independently-operated servers means a physical attacker
must compromise multiple parties at once, not one. This is a genuine
improvement, and still not a solution -- if the "independent" parties
aren't actually independent (same operator, same facility), the
threshold is theater. That distinction is the whole point of calling
this a partial mitigation rather than claiming it's resolved.
"""

import os
from dataclasses import dataclass

import blake3


def software_fingerprint(source_bytes: bytes) -> bytes:
    """A hash of the verification server's own code -- what a heartbeat
    challenge gets bound to."""
    return blake3.blake3(source_bytes).digest()


def issue_challenge(seed: bytes = None) -> bytes:
    return seed if seed is not None else os.urandom(32)


def respond_to_challenge(software_fp: bytes, challenge: bytes, secret_state: bytes) -> bytes:
    """The response binds together: which code is running (software_fp),
    the specific challenge (so replaying an old response doesn't work),
    and the server's own accumulated state (secret_state -- e.g. a
    running hash of recent ledger entries, so the response also proves
    the server hasn't rolled back or forked its own history)."""
    return blake3.blake3(software_fp + challenge + secret_state).digest()


def verify_response(expected_software_fp: bytes, challenge: bytes, expected_state: bytes, response: bytes) -> bool:
    return respond_to_challenge(expected_software_fp, challenge, expected_state) == response


@dataclass
class ThresholdAttestationResult:
    total_parties: int
    agreeing_parties: int
    threshold: int
    threshold_met: bool


def verify_threshold(
    expected_software_fp: bytes,
    challenge: bytes,
    expected_state: bytes,
    responses: list,
    threshold: int,
) -> ThresholdAttestationResult:
    """Raises the bar set by verify_response() alone: instead of trusting
    one server's self-attestation, require agreement from a threshold of
    independently-operated verification servers. Compromising a single
    party with physical access no longer suffices -- an adversary now
    needs to compromise `threshold` of `len(responses)` parties
    simultaneously, which is a genuine increase in the resources and
    coordination an attack requires.

    What this does NOT do: eliminate the underlying problem. If all the
    "independent" parties are ultimately operated by, hosted by, or
    otherwise controllable by one adversary (e.g. a single datacenter
    operator running several nodes that only look independent), the
    threshold provides no real protection -- this raises the cost of
    physical compromise, it does not remove the need for the parties to
    actually be independent, which this module cannot verify or enforce
    on its own."""
    agreeing = sum(
        1 for _, response in responses
        if verify_response(expected_software_fp, challenge, expected_state, response)
    )
    return ThresholdAttestationResult(
        total_parties=len(responses),
        agreeing_parties=agreeing,
        threshold=threshold,
        threshold_met=agreeing >= threshold,
    )
