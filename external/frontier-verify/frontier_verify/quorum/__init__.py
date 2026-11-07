"""Multi-verifier quorum: the smallest credible experiment testing
whether multiple independently-keyed verifier instances materially
improve assurance over one. See docs/research/verifier-trust.md for the
honest analysis -- this package tests IMPLEMENTATION-INSTANCE
independence (separate processes, separate keys, separate storage), not
IMPLEMENTATION-DESIGN independence (every instance still runs identical
source code). That distinction is the entire point of this experiment,
not a footnote to it."""
