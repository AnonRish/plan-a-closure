# Treaty mechanisms: what is code here, what needs a GPU or a cluster, what is not code

The proposals below describe how a halt or an international agreement on AI would work. This file takes every
mechanism they name that could be checked by a computer and says where it stands in this repository. The code is in
`src/closure/treaty/` (`closure treaty --help`), the tests are in `tests/test_treaty.py` and
`tests/test_treaty_torch.py`, and the energy, traffic and state closure that the rest of this repository builds is the
verification layer underneath them.

Sources:
[NP] ControlAI, *A Narrow Path* (2024, pdf.narrowpath.co); [DIP] ControlAI, the Direct Institutional Plan
(controlai.org/dip); [MP] Amadori, Alfour, Miotti and Behrens, *How middle powers may prevent the development of
artificial superintelligence* (asi-prevention.com, SSRN 5776982); [MV] Scher and Thiergart, *Mechanisms to Verify
International Agreements About AI Development* (MIRI, November 2024); [GE] Barnett and Scher, *AI Governance to Avoid
Extinction* (MIRI, May 2025); [EV] Barnett and Thiergart, *What AI evaluations for preventing catastrophic risks can and
cannot do* (arXiv 2412.08653); [CB] Coalition for a Baruch Plan for AI, *The Deal of the Century* (cbpai.org).

Status: **built** (implemented and tested in CI, CPU only); **runs on hardware** (written here; it means something only
on a GPU, a cluster or a second machine, and the command is given); **existing** (already in plan-a-closure before the
treaty modules); **hardware R&D** (needs chips or enclosures that do not exist yet); **not code** (law, diplomacy,
intelligence, money).

## What the computations show

These are computations from stated inputs, not forecasts. Each one is reproduced by the named test.

- **The middle-powers agreement can activate with two parties.** With World Bank GDP (2023, current US$) and
  population (2025), the EU acting as one (17.4% of world GDP, 5.5% of population) and India (3.4%, 17.8%) together
  hold 20.8% and 23.3%, past both of [MP]'s 20% thresholds. It is the only two-member coalition that does, and no
  single player does (exhaustive search; `test_the_smallest_activating_coalition_is_the_eu_and_india`). With each EU
  member counted separately, the smallest coalitions have 7 members, and every one includes India, Germany and Japan:
  the six largest economies outside the US and China hold 19.8% of world GDP, and the seven largest without Germany,
  or without Japan, stay under 20%. Without India, the smallest coalitions also have 7 members (for example the EU,
  Japan, Indonesia, Pakistan, Brazil, Bangladesh and Russia), because the six most populous players other than India
  hold 19.7% of world population. India's population is what makes the two-member coalition possible
  (`test_without_the_eu_bloc_or_without_india_seven_members_are_needed`). In Shapley-Shubik power with the US and
  China outside, the EU is 0.27 and India 0.08, then Japan 0.06 and the UK 0.04 (`closure treaty coalition`).
- **Winner-take-all needs near-certain detection.** If finishing a covert programme is worth W and being caught costs C,
  it does not pay only when verification catches it before it finishes with probability at least W / (W + C): 99% when
  winning is worth 100 times the penalty, however that detection is spread over time (`deterrence.race_threshold`). Penalty
  ladders like [MP]'s deter a race only if verification makes cumulative detection that high.
- **A sequential test catches sustained hidden load long before it adds up to a threshold run,** if residuals are
  independent: with the residual noise a 2% minimum detectable fraction implies, a load of 0.01% of capacity on
  100,000 H100s is flagged in about 37 days (one false alarm per 10 years), while reaching 1e25 FLOP at that rate would
  take about 23 years (`closure treaty race`). So the binding limit is the systematic floor (drift and model mismatch,
  which do not average out), not per-block noise: at a 0.5% floor, the same fleet could run a 1e25 FLOP training run
  in secret in about 165 days if the hidden work could be pooled (`closure treaty covert-days --gap 0.005`). Pooling
  needs gradient traffic, which the traffic closure and [MV]'s bandwidth-limited pods bound separately.
- **An energy cap is safe but loose.** In the mock training run the provider stops the job when energy divided by the
  device's energy floor reaches the budget. That never lets the job exceed its budget if the floor is a true floor, but
  the job gets only (floor / its own J per FLOP) of its budget, about 10% in the CPU drill here; a floor set too high lets
  the job run to three times its budget (`test_a_floor_that_is_not_a_floor_lets_the_job_run_past_its_budget`).
- **A Narrow Path's numbers.** Its Phase 0 licence pair (1e25 FLOP, 1e17 FLOP/s) means the largest unlicensed run
  takes 1e8 s (3.2 years) at the largest unlicensed power. Its statement that in each limit regime the largest
  permitted run "could be run as quickly as within 12 days" (p. 52) needs a ratio near 1e6 s, so it refers to the Phase 1
  limits, whose values the text does not state.

## [NP] A Narrow Path and [DIP] the Direct Institutional Plan

| mechanism | where | status | here |
| --- | --- | --- | --- |
| Training Licence above 1e25 FLOP; Compute Licence above 1e17 FLOP/s | pp. 30, 33, 36 | built | `thresholds.licences_needed` |
| Multi-Threshold System (lower, middle and upper limits, lowered over time; largest run "within 12 days") | pp. 42-44, 51-52 | partial | `thresholds.narrow_path_regime_ratio_s`; the limit values are not in the text |
| Compute reporting for training runs | p. 33 | existing | the energy closure (`closure hw-trial`), now with `covert-days` |
| Mock training runs: can the provider cut off a run that exceeds its threshold, do weights start at zero | p. 32 | built, runs on hardware | `closure treaty mock-run` (CPU in CI; `--device cuda:0 --probe probe.json` on a GPU) |
| Mock runs: detecting use of several data centres | p. 32 | not built | needs a traffic closure across sites |
| Hardware tracking: GPS trackers now, serialized secure GPUs later | pp. 37-38 | alternative built, runs on hardware | `closure treaty geo-landmark` / `geo-chip` (delay-based location) |
| Remote chip deactivation (hardware-enabled governance mechanisms) | p. 38 | hardware R&D | `closure pause` covers the hardwired-pause paper |
| Randomised spot checks of shutdown coordination | p. 37 | partial | `mock-run` (stop latency), `quorum` (who may order a stop) |
| Know-your-customer for compute providers; near-miss reporting; open-sourcing ban; liability; penalty ladder | pp. 32-38 | not code | |
| Prohibitions: superintelligence, AIs improving AIs, breakout-capable AIs, unbounded AIs; safety cases | pp. 15-29 | not code | [EV]: evaluations cannot show their absence |
| IASC: Council, Executive Board with permanent members, General Secretary by three-fourths of the Board | pp. 48-49 | partial | `quorum.majority`, `quorum.verify` (vetoes not built) |
| IASC inspections and the information framework: inspections, compute concentrations, supply-chain audits | pp. 53-55 | partial | `ledger.audit_sample_size`, `inspection` (unpredictable samples); audits are not code |
| Tamper-resistant mechanisms that flag exceptionally large compute use | p. 54 | hardware R&D; energy alternative built | `mock-run`'s energy cap |
| GUARD; the International AI Tribunal (31 judges, panels of 5, grand chamber of 15) | pp. 56-61 | not code | |
| Phase 2: science of intelligence, specification language, safe-by-design | pp. 62-68 | research | |
| DIP: policy briefs, briefing lawmakers, draft bills | controlai.org/dip | not code | its asks are NP's, above |

## [MP] How middle powers may prevent the development of ASI

| mechanism | where | status | here |
| --- | --- | --- | --- |
| Activation at 20% of world GDP and 20% of world population | s. 5 | built | `coalition.activates`, `smallest_coalitions`, `shapley_shubik` (World Bank data bundled) |
| Named chokepoints: Netherlands (EUV), South Korea (memory), Taiwan (leading-edge logic) | s. 7 | recorded | `coalition.CHOKEPOINTS`; Taiwan is not in World Bank data |
| Technical and judicial redlines and the penalty ladder | ss. 4.2, 4.3, 6.1 | built | `coalition.assess`; open thresholds are yes/no findings |
| Six months in violation escalates; a leak escalates one level; the risk-averse presumption | s. 6.1, 6.2 | built | `coalition.run_timeline`, `presumed_level` |
| Impromptu session at a fifth of members plus one; amendments by supermajority | s. 6 | partial | `coalition.impromptu_session`; the supermajority is not specified |
| Escalation in unison; no Security Council requirement; self-defence right | ss. 4.2-4.3 | not code | |
| Trade restrictions, cost-sharing, API access to a joint lab | ss. 4.1, 7 | not code | |
| Monitoring: supply chains, thermal satellite imaging, intelligence sharing | s. 6.2 | not code | the rates verification allows: `covert-days` |
| Stag hunt and winner-take-all reasoning | motivation, adoption | built | `deterrence` (per-period and race conditions, checked by simulation) |

## [MV] Mechanisms to Verify International Agreements About AI Development

| mechanism | status | here |
| --- | --- | --- |
| Chip ownership and location registry | existing | `ledger.StockLedger`, `ledger.reconcile` (chip-stock accounting with uncertainty) |
| Physical inspection of a random sample of declared chips | existing, extended | `ledger.audit_sample_size`; `inspection` adds repeated inspections and samples the inspected party cannot predict (`plan_sample` from a `beacon` seed), and the two implementations are checked against each other |
| Ping-based location tracking | built, runs on hardware | `geoloc`; landmarks on reachable hosts, the chip connects out |
| Chip-adjacent FlexHEG location attestation; tamper-evident chips; continuous monitoring with portals and cameras | hardware R&D | |
| Supply-chain registry and chain of custody | partial | the hash-chained, signed evidence format (`evidence.py`) |
| Exclusion of compute that cannot run a large training run | built | `thresholds.run_flop`, `seconds_to` |
| Emergency shutdown, checked by power draw | existing | `dcbus.py` (independent DC-bus meter), NVML |
| Compute accounting: few unverified chip-hours remain | existing | the energy and busy-time closure, `covert-days`, `race` |
| Partial re-running of declared work | existing | `repro.py`, `taphash.py`, `assurance.py` |
| Workload classification from power, bandwidth, utilisation, precision | existing | `cadence-check`; closure itself is signature-independent |
| Interconnect bandwidth limits (pods of about 128 chips) | partial | `traffic.py` (traffic closure); a bandwidth-needed calculator is not built |
| Hardware FLOP utilisation | existing | the trial's busy-time channel |
| Inference-only chips; FlexHEG workload classification; allow-listed operations | hardware R&D | |
| TEEs, model hashing and signing, cryptographic audit trails | partial | signing and hash chains (`evidence.py`); TEEs are hardware |
| Whistleblowers, interviews, intelligence, inspector code access | not code | |
| AI-enabled verification; model behaviour specifications | research | |

## [GE] AI Governance to Avoid Extinction: research questions this code bears on

| question (section) | status | here |
| --- | --- | --- |
| How can governments monitor compute they know about, so it is not used to violate a Halt? (2.3.3) | partial | the energy closure; `covert-days`; `race`; `mock-run` |
| How can countries verify the presence and completeness of declared clusters? (2.3.3) | partial | `inspection` (presence), `geoloc` (location), energy closure (one site); grid-level completeness is not built |
| What compute needs to be monitored after a Halt is initiated? (2.3.3) | partial | `thresholds.run_flop` |
| What is the minimum viable Off Switch? (2.1) | partial | `mock-run` (stop at a budget), `quorum` (who orders it), `closure pause` |
| What is the breakout time for secret AI chip development? (2.3.3) | not built | needs fab data |
| Threat of Sabotage regime (4.2) | partial | `deterrence.race_threshold`: what detection a sabotage threat needs |

## [EV] What AI evaluations can and cannot do

Evaluations give lower bounds on capabilities, not upper bounds. So a judicial redline in [MP] (an engineer speed-up,
an automation level) can be established by an evaluation that finds it and never ruled out by one that does not; the
redline engine takes panel findings as given and does not treat an absent finding as evidence of absence. The paper's
recommendations (audits with full affordances, conservative red lines, security, monitoring for misalignment) are not
code.

## [CB] The Deal of the Century

| mechanism | status | here |
| --- | --- | --- |
| "A cap on the frontier, not deployment"; Beijing's draft 1e26 FLOP threshold, as cited | built | `thresholds.THRESHOLDS["beijing-draft"]`, `covert-days --threshold 1e26` |
| "Suspended enforcement clauses", switched on when a joint scientific panel finds a threshold crossed | partial | `quorum.verify` for the panel's signed finding; `coalition.assess` for a ladder |
| Citizen witnesses, lot-selected and multinational | built | `beacon.sortition` (stratified by group, from a commit-reveal seed) |
| Critical actions require multiple people; air-gapped multi-party controls | built | `quorum` (k-of-n Ed25519 approval) |
| Hardware roots of trust with public attestation; formally verified open stacks | hardware R&D, research | |
| A secure joint network for alerts and verification data; an incident rulebook | not built | signed hash chains (`evidence.py`) are a starting point |
| Half of every new dollar of frontier-lab value held by citizens; a GDP-weighted convention | not code | GDP shares: `coalition.players` |

## What runs on a GPU or a cluster

| command | needs | what a run decides |
| --- | --- | --- |
| `closure tier0` | one GPU with root (Colab T4 for a shakedown; an instrumented H100 for the pilot) | whether energy tracks verified work, the slack and energy floor, residency, the smoke trial |
| `closure treaty mock-run --device cuda:0 --probe runs/.../probe.json --budget-flop 1e16` | the same GPU, after hw-probe | whether a provider can stop a run at its compute budget from energy alone, and how loose the cap is |
| `closure treaty geo-landmark` on reachable hosts, `geo-chip` on the GPU node | two or more machines with known locations | how close the node is proven to be to its declared site |
| `closure treaty covert-days --run runs/.../T1-smoke` | a finished trial | days a fleet of a given size needs to run a threshold-sized covert run below detection |
