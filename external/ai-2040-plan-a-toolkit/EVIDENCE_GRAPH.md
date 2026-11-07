# Common evidence graph

The four tracks share a typed provenance graph:

Observation -> Evidence -> Claim -> Verification procedure -> Result -> Attestation -> Receipt

Every node carries an integrity digest, and evidence may carry an independence
group and maturity level. Claim support is computed from actual supporting nodes.

Causal cycles are rejected. The graph root digest provides one content-addressed
identity for the evidence topology.

The graph is a provenance structure, not proof that a physical observation was
truthful.
