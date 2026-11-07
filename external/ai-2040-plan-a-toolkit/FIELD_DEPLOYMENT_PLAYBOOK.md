
# Field deployment playbook

This is the operational bridge between RVP-1 software and a real verification
deployment.

## Before installation

Freeze the protocol version and verifier public keys. Assign immutable asset
IDs. Record supplier, hardware revision, firmware version, expected
configuration digest, serial number, custody events and spare count. Bench-test
each unit before it enters the deployment pool.

## Installation

Two-person installation is the minimum proposed control for high-stakes sites.
The installer records port mapping, optical path, endpoint identities, enclosure
state, firmware measurement and initial challenge result. An independent
inspector signs the installation evidence.

## Acceptance

A device is not ACCEPTED merely because it is powered on. It must pass the
configuration, link, tamper and reporting checks, and the raw evidence must be
archived. Failed or ambiguous installations remain UNKNOWN.

## Continuous operation

Re-challenge configuration, enclosure state, link health and verifier reporting
on a defined cadence. Rotate signing keys according to the security policy and
record every key transition. Maintain spare capacity so a suspect unit can be
removed without losing coverage.

## Incident response

Any unexpected traffic, configuration drift, missing health checks, broken
report chain, unexpected reboot, enclosure event or monitor outage creates an
explicit finding. The default response is fail-closed or UNKNOWN according to
the protocol, never silent continuation.

## Scale-up

For a government-scale deployment, maintain manufacturing qualification,
incoming acceptance testing, serialized asset tracking, secure firmware
provisioning, spare stock, installer training, independent inspection teams and
a decommissioning process.

The playbook is a design artifact. It does not constitute physical inspection
authority or prove that these controls work at scale.
