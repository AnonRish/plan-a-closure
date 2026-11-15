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
cannot do* (arXiv 2412.08653); [CB] Coalition for a Baruch Plan for AI, *The Deal of the Century* (cbpai.org); [MA]
Scher, Abecassis, Barnett and Abeyta, *An International Agreement to Prevent the Premature Creation of Artificial
Superintelligence* (MIRI Technical Governance Team, arXiv 2511.10783, v3); [FLI] Future of Life Institute with the
Centre for International Governance Innovation, *Draft Articles on the Safe Development and Diffusion of Artificial
Intelligence* (web version 2, 18 June 2026, global-governance.ai). [MA] and [FLI] are written as treaty text, so they are
mapped article by article in a generated matrix, [AGREEMENTS_COVERAGE.md](AGREEMENTS_COVERAGE.md) (`closure treaty
coverage`, which fails if a row points at code or a test that does not exist); the sections for them below summarise it.

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
  (`test_without_the_eu_bloc_or_without_india_seven_members_are_needed`). Each "smallest" here is proved, not only
  searched for: no coalition can be smaller than the number of players it takes to reach both quotas when the largest
  are taken first (`coalition.size_bound`), and `closure treaty coalition` prints that bound with what it finds
  (`--exclude USA,CHN,IND` and `--no-bloc` reproduce the two seven-member results). In Shapley-Shubik power with the US and
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
- **[FLI]'s chip authorization, as written, can be stockpiled.** Annex C's commentary describes an authorization as a
  file naming the chip, a number of allowed clock cycles and an identification number the chip has not seen before, as
  in Petrie's firmware design (2024). Nothing stops a provider from taking delivery of every renewal and handing the
  chip one only when it runs low, so when renewal stops after a verified violation the chip runs on for as long as the
  unused authorizations last, not until "the next clock cycle". With renewals every 5 minutes, each worth 10 minutes so
  that one late renewal does not stop a compliant chip, a chip that has run for 30 days runs on for 30 days; with
  6-minute authorizations, 6 days; with no margin at all, a chip used at 90% of full speed banks 3 days a month. A cap
  on the allowance a chip stores does not help, because the stockpile is outside the chip. Binding each authorization to
  a nonce the chip has just generated and is waiting on (as Petrie's later security-block design does, 2025), together
  with a cap, bounds the run-on to about one renewal period however long the chip has been in use
  (`chipauth.simulate`, `closure treaty chip-auth`; the arithmetic is `chipauth.bank_days`).
- **[MA]'s 25 Gbit/s line does not make training across small clusters difficult.** Art. II s.16 covers more than 16
  H100e, networked by co-location, by more than 25 Gbit/s between hosts, or by running a workload together; its note
  says the bounds should make training across sub-CCC sets of chips difficult. Two sets of 16 H100e on a 25 Gbit/s link
  are not a covered cluster by size or by bandwidth, yet synchronous data-parallel training across them at 40%
  utilization and a 4M-token batch needs 8.4 Gbit/s, so the link does not slow it at all; a 1M-token batch needs 34
  Gbit/s, a 1.35x slowdown; synchronising every 100 steps instead of every step needs 0.08 Gbit/s, and under 1 Gbit/s a
  site for ten such sets. The model's size cancels out (`closure treaty asi-crosssite`). What catches such a run is the
  third test, "networked to perform workloads together", and that needs knowing what the chips run: the traffic and
  energy closure this repository builds. Art. VIII s.1(b) restricts research on distributed training, but
  low-communication training (for example DiLoCo, Douillard et al. 2023) is already published.
- **On [MA]'s plain reading, a Council member can refuse a challenge inspection of its own territory.** A challenge
  inspection needs the Executive Council's consensus (Art. X s.3(b)), the Council is initially the U.S. and the PRC
  (Art. III s.3(a)), and the text does not exclude the Party to be inspected; the inspectors must also be approved by
  the inspected Party (s.3(d)). `ChallengeInspections(exclude_inspected=True)` is the other reading. "At most 20 times per
  year" (s.3(e)) read as a calendar year allows 40 inspections within three weeks around 1 January; a rolling year
  allows 20.
- **[FLI]'s weighted votes put verification and enforcement in few hands.** Most Conference decisions are one vote per
  State, but the Director-General, the Agency's rules and the approval or amendment of verification and enforcement
  mechanisms are weighted by contributions to the Fund (Art. 12(7)). Contributions come from a tax on AI gains that
  nobody can measure yet; with GDP as a stand-in (World Bank 2023) and every economy a party, the U.S., China, Germany
  and Japan hold 51% of the weighted vote and decide those matters alone, with Shapley-Shubik power 0.32 for the U.S. and
  0.17 for China (`closure treaty fli-weighted`). AI gains are likely more concentrated than GDP, which would put the
  same matters in even fewer hands.
- **[MA]'s Tables 1 and 2 reproduce exactly at 990 TFLOP/s per H100e.** With the agreement's own 989 TFLOP/s (Art. II
  s.15), four cells change in the last printed digit: 117.0, not 116.9, days for one H100e to reach the Monitored
  Threshold, and 117.0, 731.4 and 11,702.8, not 116.9, 730.7 and 11,691.0, days for 100, 16 and 1 H100e to reach the
  Strict Threshold. Table 1 schedules clusters of 16 H100e for registration in Year 2, but Art. II s.16 covers only
  clusters of more than 16, so a cluster of exactly 16 is never covered; Appendix D.3.1 likewise says "above 10,000"
  where Table 1 puts 10,000 on Day 1 (`closure treaty asi-tables`, `--boundaries text`).

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
| Ping-based location tracking | built, runs on hardware | `geoloc`; landmarks on reachable hosts, the chip connects out. Tested over TCP on one host; no run between machines in different places is on record |
| Chip-adjacent FlexHEG location attestation; tamper-evident chips; continuous monitoring with portals and cameras | hardware R&D | |
| Supply-chain registry and chain of custody | partial | the hash-chained, signed evidence format (`evidence.py`) |
| Exclusion of compute that cannot run a large training run | built | `thresholds.run_flop`, `seconds_to` |
| Emergency shutdown, checked by power draw | existing | `dcbus.py` (independent DC-bus meter), NVML |
| Compute accounting: few unverified chip-hours remain | existing | the energy and busy-time closure, `covert-days`, `race` |
| Partial re-running of declared work | existing | `repro.py`, `taphash.py`, `assurance.py` |
| Workload classification from power, bandwidth, utilisation, precision | existing | `cadence-check`; closure itself is signature-independent |
| Interconnect bandwidth limits (pods of about 128 chips) | built (the arithmetic), existing (the measurement) | `treaty/bandwidth.py`, `closure treaty bandwidth`: the link rate that data-parallel training across pods needs for a given model size, step rate and compression, the slowdown a cap forces, and the rate inference needs, for comparison; `traffic.py` measures what a link carried |
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
| "Suspended enforcement clauses", switched on when a joint scientific panel finds a threshold crossed | built | `treaty/clauses.py`, `closure treaty clause`: a clause is in force only for a finding that k of the n panel members signed and that has not expired, and the finding maps to a ladder level (`coalition.assess`); a month-by-month timeline keeps the persistence rules |
| Citizen witnesses, lot-selected and multinational | built | `beacon.sortition` (stratified by group, from a commit-reveal seed). A party that reveals last could withhold and force a rerun it likes better, so a missing reveal is named (`beacon.missing`) and a draw is finalised with a public value fixed after the last reveal (`beacon.finalize`), which the last revealer cannot steer |
| Critical actions require multiple people; air-gapped multi-party controls | built | `quorum` (k-of-n Ed25519 approval) |
| Hardware roots of trust with public attestation; formally verified open stacks | hardware R&D, research | |
| A secure joint network for alerts and verification data; an incident rulebook | not built | signed hash chains (`evidence.py`) are a starting point |
| Half of every new dollar of frontier-lab value held by citizens; a GDP-weighted convention | not code | GDP shares: `coalition.players` |

## [MA] MIRI's draft agreement, arXiv 2511.10783

Every article (I to XV) and the paper's Appendix D.3 has a row in [AGREEMENTS_COVERAGE.md](AGREEMENTS_COVERAGE.md). The
code is `treaty/asi_agreement.py` and `treaty/obligations.py`; the tests are in `tests/test_treaty_agreements.py`.

| mechanism | where | status | here |
| --- | --- | --- | --- |
| FLOP counting, H100e and TPP, advanced chips, the three thresholds | Art. II ss.4, 8-11, 15 | built | `counted_flop`, `tpp`, `chip_tpp`, `is_advanced_chip`, `classify_run` (`closure treaty asi-run`) |
| Covered chip clusters: compute or memory, co-location, more than 25 Gbit/s, shared work | Art. II s.16 | built | `covered_clusters` (`asi-cluster`); `cross_site_training_gbps` (`asi-crosssite`) for the note on training across sub-CCC sets |
| Declared runs: code, data, FLOP estimate; approval by inspectors of both sides; the technique whitelist | Art. IV s.2, Art. II s.20 | built | `declaration`, `approve_monitored_run` (Ed25519, either side may withhold); `within_declaration` against a mock run |
| Council consensus, vetoes over the CTB, 30-day emergency changes, the Director-General's term | Art. III ss.3-4 | built | `council_consensus`, `ctb_decision_stands`, `thresholds_in_force`, `obligations.term_problems` |
| Register (120 days, then at least every 90), consolidation, transfers (14 days, CTB approval), certified destruction | Art. V ss.3-7, Art. VI ss.4-6 | built | `register_problems`, `transfer_check`, `ChipStock`, `obligations.check` |
| Production monitoring | Art. VI ss.1-3 | partial | the hardwired-pause layer's fab accounting (`pause/fab.py`); inspectors in fabs are physical |
| Continuous on-site verification; powered-off hardware verified continually | Art. VII ss.1-3 | runs on hardware | the energy, traffic and state closure; `powered_off` over an independent meter's trace (`asi-off`) |
| Challenge inspections: consensus, 24 hours, inspectors both sides approve, 20 a year | Art. X s.3 | built | `ChallengeInspections`, `access_in_time`; both readings of the consensus and of "per year" |
| Dispute deadlines (36 hours, 5 days), review conferences, withdrawal (12 months) | Arts. XI, XIV, XV | built | `obligations.check` (`closure treaty obligations`) |
| Protective Action Statements | Art. XII s.6 | built | `statement_problems`; the actions themselves are not code |
| Tables 1 and 2, staged registration, the FP8 note | Appendix D.3 | built | `tables`, `compare_tables`, `registration_stage`, `fp8_note_days` (`asi-tables`) |
| Research restrictions and their verification, information consolidation, protective actions, CTB reviews | Arts. VIII, IX, X ss.1-2, XII, XIII | not code | |

## [FLI] FLI's Draft Articles

Every article (1 to 18) and annex (A, B.1, B.2, C.1, C.2) has a row in [AGREEMENTS_COVERAGE.md](AGREEMENTS_COVERAGE.md).
The code is `treaty/fli_articles.py`, `treaty/chipauth.py` and `treaty/obligations.py`. The draft sets no compute
threshold: its trigger is Annex A's list of uses, risks and capabilities, which an evaluation can find but not rule out
([EV]).

| mechanism | where | status | here |
| --- | --- | --- | --- |
| Global catastrophic risk: more than 50 people or more than USD 1 billion, in a single incident | Art. 2 | built | `is_global_catastrophic` |
| Investigate before enforcing unless a global catastrophic risk is suspected; the burden reverts | Art. 6 | built | `enforcement_may_start`, `enforcement_must_lift`, `chipauth.Enforcer.resume` |
| Certificates renewed every six months by licensed evaluators; challenges by States Parties decided within a week; provisional suspension; tax evaders ineligible | Arts. 7, 10(5) | built | `Certificates`, `licence_problems`, `obligations.check` |
| The 5% tax; the Agency's 1%; the Director-General's term | Arts. 10(4), 13(3), 13(10) | built | `tax_compliant`, `agency_funding`, `obligations.term_problems` |
| Quarterly sessions, rules of procedure in 15 days, extraordinary sessions at a third, simple and weighted majorities | Art. 12 | built | `obligations.check`, `extraordinary_session`, `conference_decision`, `fewest_to_decide`, `weighted_power` (`fli-weighted`) |
| Amendments by two thirds; the Agency may not recommend removing an Annex A item | Art. 15 | built | `amendment_adopted`, `annex_a_change_problems` |
| Chip registry with unique IDs and declared locations; delay-based location; on-site inspections | Annex B.1(1)(c)-(e) | built, runs on hardware | `registry_problems`, `pause/registry.py`, `geoloc`, `inspection` |
| Digital perimeter that verifies all traffic; commitments inside it | Annex B.2 | runs on hardware; built | `traffic.py`; `evidence.commit` |
| Neutral data centres, air-gapping, encrypting gateways, tamper-evident hardware | Annex B.2 | physical | |
| Chip authorizations signed by the State (C.1) or the Agency (C.2), used once, renewed every few minutes, withheld after a verified violation; firmware updates | Annexes C.1, C.2 | built (software stand-in) | `chipauth.GuaranteeProcessor`, `Enforcer`, `simulate`, `firmware_update` (`closure treaty chip-auth`) |
| Tamper-proof enclosures and fuses | Annexes C.1, C.2 | hardware R&D | modelled as a flag |
| Safety standards, emergency cooperation, benefit sharing, the Fund, the Panel, universality | Arts. 1, 3-5, 7(1)-(3), 8, 9, 11, 13, 14, 16-18 | not code | |

## What runs on a GPU or a cluster

| command | needs | what a run decides |
| --- | --- | --- |
| `closure tier0` | one GPU with root (Colab T4 for a shakedown; an instrumented H100 for the pilot) | whether energy tracks verified work, the slack and energy floor, residency, the smoke trial |
| `closure treaty mock-run --device cuda:0 --probe runs/.../probe.json --budget-flop 1e16` | the same GPU, after hw-probe | whether a provider can stop a run at its compute budget from energy alone, and how loose the cap is |
| `closure treaty geo-landmark` on reachable hosts, `geo-chip` on the GPU node | two or more machines with known locations | how close the node is proven to be to its declared site |
| `closure treaty covert-days --run runs/.../T1-smoke` | a finished trial | days a fleet of a given size needs to run a threshold-sized covert run below detection |
| `closure meter-log --out bus.dump --csv bus.csv`, then `closure treaty asi-off --csv bus.csv --off-w <W>` | a PowerSensor3 (or any DC-coupled meter) on a rig that should be off | [MA] Art. VII s.3: whether the hardware stayed off for every second the trace covers, with no gap in the record |
