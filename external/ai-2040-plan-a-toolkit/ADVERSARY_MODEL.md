# RVP-1 adversary model

Verification is modeled as an adversarial measurement problem. The catalog covers NETWORK, COMPUTE, STORAGE, FIRMWARE, PHYSICAL, SUPPLY_CHAIN, VERIFIER, SAMPLING_FRAME and TELEMETRY.

Every preregistered case has a safe outcome class of FAIL, UNKNOWN or INVESTIGATE and an explicit control path. Common-mode groups are recorded so nominally separate controls are not automatically treated as statistically independent.

The executable module adversary/model.py is the catalog and coverage gate.
