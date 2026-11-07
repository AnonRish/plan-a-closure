
---- MODULE PlanAVerification ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANT Packets

VARIABLES phase, commitment, challenge, result, evidence

Phases == {"OPEN", "COMMITTED", "CHALLENGED", "CHECKED", "TERMINAL"}
Results == {"NONE", "PASS", "FAIL", "UNKNOWN"}

Init ==
    /\ phase = "OPEN"
    /\ commitment = 0
    /\ challenge = 0
    /\ result = "NONE"
    /\ evidence = {}

Commit(c) ==
    /\ phase = "OPEN"
    /\ c \in Nat
    /\ c > 0
    /\ commitment' = c
    /\ phase' = "COMMITTED"
    /\ UNCHANGED <<challenge, result, evidence>>

Reveal(ch) ==
    /\ phase = "COMMITTED"
    /\ ch \in Nat
    /\ ch > 0
    /\ challenge' = ch
    /\ phase' = "CHALLENGED"
    /\ UNCHANGED <<commitment, result, evidence>>

Check(r, e) ==
    /\ phase = "CHALLENGED"
    /\ r \in Results \ {"NONE"}
    /\ e \in SUBSET Packets
    /\ result' = r
    /\ evidence' = e
    /\ phase' = "CHECKED"
    /\ UNCHANGED <<commitment, challenge>>

Finalize ==
    /\ phase = "CHECKED"
    /\ phase' = "TERMINAL"
    /\ UNCHANGED <<commitment, challenge, result, evidence>>

Next ==
    \/ \E c \in Nat : Commit(c)
    \/ \E ch \in Nat : Reveal(ch)
    \/ \E r \in Results, e \in SUBSET Packets : Check(r, e)
    \/ Finalize

Spec == Init /\ [][Next]_<<phase, commitment, challenge, result, evidence>>

CommitBeforeChallenge ==
    phase \in {"CHALLENGED", "CHECKED", "TERMINAL"} => commitment > 0

ChallengeBeforeCheck ==
    phase \in {"CHECKED", "TERMINAL"} => challenge > 0

NoPassWithoutEvidence ==
    result = "PASS" => Cardinality(evidence) > 0

TerminalRequiresChecked ==
    phase = "TERMINAL" => result \in Results \ {"NONE"}

Safety ==
    CommitBeforeChallenge
    /\ ChallengeBeforeCheck
    /\ NoPassWithoutEvidence
    /\ TerminalRequiresChecked

====
