# Hardware-rooted compute meter interface

This package defines a vendor-neutral evidence interface for hardware counters.
A production adapter supplies real accelerator counters and, where available,
hardware attestation binding the counters to a device identity.

The verifier checks:
- device identity continuity;
- counter monotonicity;
- explicit reset epochs;
- accelerator-family/model matching;
- conversion model version;
- timestamp provenance;
- attestation reference.

The module does not invent FLOP counts and does not assume that a vendor counter
is impossible for an operator to manipulate. Those are separate hardware-root
and audit assumptions.

A field deployment should calibrate the FLOP model against independently
measured workloads and publish the calibration evidence.
