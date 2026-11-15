"""Mechanisms from the halt and treaty proposals, made concrete enough to compute, test or run.

Sources (docs/TREATY_COVERAGE.md maps every mechanism they name to code, to a hardware or cluster step, or to "not
code"):

* ControlAI, *A Narrow Path* (2024) and the Direct Institutional Plan (controlai.org/dip);
* Amadori, Alfour, Miotti and Behrens, *How middle powers may prevent the development of artificial superintelligence*
  (asi-prevention.com, SSRN 5776982);
* Scher and Thiergart, *Mechanisms to Verify International Agreements About AI Development* (MIRI, November 2024);
* Barnett and Scher, *AI Governance to Avoid Extinction* (MIRI, May 2025);
* Barnett and Thiergart, *What AI evaluations for preventing catastrophic risks can and cannot do* (arXiv 2412.08653);
* the Coalition for a Baruch Plan for AI, *The Deal of the Century* (cbpai.org);
* Scher, Abecassis, Barnett and Abeyta, *An International Agreement to Prevent the Premature Creation of Artificial
  Superintelligence* (MIRI Technical Governance Team, arXiv:2511.10783);
* the Future of Life Institute with the Centre for International Governance Innovation, *Draft Articles on the Safe
  Development and Diffusion of Artificial Intelligence* (2026).

The last two are mapped article by article in docs/AGREEMENTS_COVERAGE.md (``coverage``).

Modules: ``thresholds`` (compute thresholds and how fast hidden compute reaches them), ``deterrence`` (when
verification deters a covert programme), ``inspection`` (random-sample chip inspections), ``beacon`` (commit-reveal
randomness and sortition), ``quorum`` (k-of-n approval of critical actions), ``geoloc`` (delay-based chip location),
``coalition`` (the middle-powers agreement's activation threshold, voting power and redline ladder), ``mockrun``
(Narrow Path's mock training runs: can the provider stop a run at its compute budget?), ``clauses`` (suspended
enforcement clauses), ``bandwidth`` (interconnect limits), ``asi_agreement`` (MIRI's draft agreement), ``fli_articles``
(FLI's Draft Articles), ``chipauth`` (their Annex C chip authorization), ``obligations`` (both texts' deadlines) and
``coverage`` (the article-by-article matrix).
"""
