# Track 3 evidence correction and dispute process

Corrections are append-only. A correction never deletes or silently edits the historical record.

Submit a GitHub issue using **Evidence correction / dispute** and provide the facility/request ID, evidence or verification ID, supporting public source, exact proposed change, and rationale.

The maintainer process is:
1. preserve the original record and snapshot;
2. record the dispute against the exact claim/evidence ID;
3. assess the supplied source against the published verification protocol;
4. publish a superseding correction record referencing the original;
5. retain both historical versions in Git history.

A correction may change a current verification result, but it does not retroactively alter the evidence state that was published at an earlier commit.

Human review is only claimed when a reviewer is explicitly recorded in the correction/audit record.
