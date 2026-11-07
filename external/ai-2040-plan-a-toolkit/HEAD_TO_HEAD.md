
# Head-to-head evaluation

The benchmark package now contains an external Amodo baseline record and a
comparison helper, but no local result is substituted for that published
measurement.

A credible comparison requires matching:
- line rate and physical interface;
- packet-size and traffic mix;
- concurrency;
- inference model and request distribution;
- verifier/prover hardware;
- capture software;
- timing and CPU/DPU accounting.

Only then should throughput, capture loss, verifier compute advantage and
detection performance be compared.

A published baseline remains attributed to its original source.
