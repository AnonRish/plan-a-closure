# Track 3 ownership graph

The software layer represents compute-relevant physical inventory as a double-entry graph.

start position + incoming transfers = end position + outgoing transfers + terminal dispositions.

Transfers are single logical events with source and destination implications. Normal resale cycles are allowed. Unbalanced inventory, duplicate identifiers, negative quantities and missing evidence block a PASS-level closure.

A balanced graph with an open population is UNKNOWN, not PASS. Accounting the declared world is not the same thing as proving the declared world is complete.
