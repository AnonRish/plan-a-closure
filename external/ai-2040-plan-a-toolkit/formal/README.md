# Formal model

PlanAVerification.tla is a compact state-machine specification of the
commit -> challenge -> check -> terminal lifecycle.

The Python reference model is the executable conformance target used in CI.
The TLA+ file is supplied so an independent evaluator can run TLC and add
stronger temporal properties, fairness assumptions, and attacker actions.

This repository does not claim that TLC has proven the entire AI 2040
verification problem. The point is to make protocol state transitions and
safety invariants explicit enough to model-check.
