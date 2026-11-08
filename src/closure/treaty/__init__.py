"""Mechanisms from the halt and treaty proposals, made concrete enough to compute, test or run.

Sources (docs/TREATY_COVERAGE.md maps every mechanism they name to code, to a hardware or cluster step, or to "not
code"):

* ControlAI, *A Narrow Path* (2024) and the Direct Institutional Plan (controlai.org/dip);
* Amadori, Alfour, Miotti and Behrens, *How middle powers may prevent the development of artificial superintelligence*
  (asi-prevention.com, SSRN 5776982);
* Scher and Thiergart, *Mechanisms to Verify International Agreements About AI Development* (MIRI, November 2024);
* Barnett and Scher, *AI Governance to Avoid Extinction* (MIRI, May 2025);
* Barnett and Thiergart, *What AI evaluations for preventing catastrophic risks can and cannot do* (arXiv 2412.08653);
* the Coalition for a Baruch Plan for AI, *The Deal of the Century* (cbpai.org).

Modules: ``thresholds`` (compute thresholds and how fast hidden compute reaches them), ``deterrence`` (when
verification deters a covert programme), ``inspection`` (random-sample chip inspections), ``beacon`` (commit-reveal
randomness and sortition), ``quorum`` (k-of-n approval of critical actions), ``geoloc`` (delay-based chip location),
``coalition`` (the middle-powers agreement's activation threshold, voting power and redline ladder) and ``mockrun``
(Narrow Path's mock training runs: can the provider stop a run at its compute budget?).
"""
