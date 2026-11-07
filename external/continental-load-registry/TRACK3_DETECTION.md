# Track 3 detection/verification implementation notes

Current published detection snapshot: 93 Epoch facilities plus a 1,015-row queue/request surveillance population without a conservative direct Epoch name match.

Current automated claim results: 744 claim records across 93 facilities. PASS results are restricted to claim-specific evidence references; end-to-end Track 3 accountability remains UNKNOWN until an independent verifier and complete physical/electrical/compute chain are present.

The repository deliberately distinguishes:
- publisher classification from physical verification;
- site-specific connection evidence from jurisdiction-only coverage;
- source availability from actual ingestion;
- corroboration metadata from methodological independence;
- absence-search documentation from an assertion that no evidence exists.

See `data/track3/verification_protocol.json`, `data/track3/detection_universe.json`, `data/track3/absence_testing.json`, and `data/track3/verification_results.json`.
