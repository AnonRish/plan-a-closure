# covert-timing-warden

Timing covert channels in a tapped inference cluster: how to detect them, how much they can leak, and what
"shielding plus noise" actually buys. Built against two workstreams that the
[Plan A get-involved page](https://ai-2040.com/supplements/verification-plan/get-involved) grades **not on track**:
*side-channel wardens* ("scanning and observing side channels to detect covert communication is unexplored") and
*side-channel mitigation (shielding plus noise)* ("only early theoretical pieces exist").
Network-timing channels only. NVLink contention, power, packet sizes and content steganography are out of scope.

Related work in `AnonRish/fides` (`warden.py`) detects injected *periodic* signals in telemetry streams by autocorrelation and
spectrum, and its docs call shielding "out of software's reach". This repository is a different slice of the same workstreams:
statistical detectors for inter-packet-delay channels with finite-sample-valid p-values, and quantitative brackets for what the
software-defined half of "shielding plus noise" (quantisation, jitter, fixed schedules) can and cannot guarantee. The
noise-injection discussion in `AnonRish/ai-2040-verification` argues qualitatively that jitter raises the noise floor; the
brackets here put numbers on that. Physical shielding of power, EM and NVLink channels is still hardware, and this repository does
not touch it.

Python 3.10+, NumPy, SciPy. 115 tests. Everything runs on synthetic traffic; **no real inference server was measured.**

```
pip install .            # console script: covert-timing-warden
```

## What it found

`covert-timing-warden demo` (real output, alpha = 0.05, 200-delay windows, 400 windows per row, reference of 520 null windows):

| scenario | alarm rate |
| --- | --- |
| honest i.i.d. traffic (false alarms) | 0.030 |
| honest bursty traffic (false alarms) | 0.038 |
| naive 4-level channel, 2 bits/packet | **1.000** |
| delays drawn with *exactly* the honest distribution, 1 bit/packet | 0.028 |
| same, 3 bits/packet | 0.050 |
| matches the honest *marginal* only, honest traffic is bursty, 2 bits/packet | **1.000** |

1. **Detection cannot bound capacity.** A channel that picks which quantile of the honest delay distribution each packet
   lands in has exactly the honest distribution (`QuantileChannel`; proof in its docstring), so no test can beat chance at
   any rate. The detectors catch what published detectors were built for and nothing cleverer. The right question is how
   much a receiver can *read*, which is what the bounds answer.
2. **Matching the marginal is not enough against structured traffic.** Dependence-sensitive statistics (lag-1 autocorrelation,
   corrected conditional entropy) catch a marginal-only adversary in every window, while the marginal test (KS) stays blind.
3. **Noise buys leakage only logarithmically.** With up to D = 500 ms of sender-controlled delay, 5 ms of uniform release
   jitter still leaves between **6.66 and 6.67 bits per packet**; 10 ms clock quantisation leaves **5.67**. Quantisation alone
   never drops below 1 bit per packet in the upper bound for any D > 0 (a sender that knows the clock phase can straddle a tick).
   Ten times the jitter buys about 3.3 bits.
4. **Only a fixed release schedule with padding reaches zero**, at the price of latency (mean Δ/2 uncongested, unbounded once
   real traffic exceeds one packet per period) and constant bandwidth.
5. **A per-delay capacity bound is not safe.** Jitter is added to timestamps. A receiver with a shared clock decodes cumulative
   timestamps and beats the memoryless per-delay bound by 20 to 36 % (`examples/why_per_ipd_is_unsafe.py`, real output):

```
 D/w  naive per-IPD BA  achieved (simulated)  proven upper  naive misses
   1            0.6360                1.0000        1.5850           36%
   2            1.1194                1.5850        2.0000           29%
   3            1.4767                2.0000        2.3219           26%
   4            1.7612                2.3219        2.5850           24%
   8            2.5378                3.1699        3.3219           20%
```

Scale matters as much as rate: 1 TB (8e12 bits) at 6.6 bits/packet, 50 packets/s, 1,000 concurrent streams takes 281 days
(`covert-timing-warden exfil`), if an accomplice can observe and separate every stream.

## Use

```python
import numpy as np
from covert_timing_warden import (Warden, LogNormalIID, QuantileChannel, UniformJitter, QuantizedRelease,
                                  FixedSchedule, blahut_arimoto, exfiltration_seconds)

honest = LogNormalIID().sample(2 * 520 * 200, np.random.default_rng(0))
w = Warden(honest, window=200, alpha=0.05)          # raises if the reference is too short to ever alarm
w.test(candidate_window_of_200_delays)              # per-detector conformal p-values, Bonferroni-combined

UniformJitter(0.005).capacity(0.5)                  # CapacityBound(lower_bits=6.658, upper_bits=6.672, ...)
QuantizedRelease(0.01).capacity(0.5)                # [5.672, 5.672]
FixedSchedule(0.02).capacity()                      # [0, 0], with latency: .latency(arrivals), .is_stable(rate)

blahut_arimoto(P)                                   # certified bracket on the capacity of any channel matrix P[x, y]
```

CLI: `bounds`, `exfil`, `detect --reference ref.csv --candidate cand.csv` (timestamp CSVs), `demo`.

## What is in it

| module | contents |
| --- | --- |
| `capacity` | Blahut-Arimoto returning a bracket `[lower, upper]` (only "converged" when narrower than the tolerance), closed forms (BSC, BEC, Z-channel, uniform noise), AWGN-PAM mutual information, plug-in MI estimator with Miller-Madow correction |
| `traffic` | i.i.d. lognormal and bursty (Markov-modulated) honest generators; CSV loader that refuses to shorten a trace silently |
| `channels` | naive level channel; quantile channel (exactly honest marginal) |
| `stats` | regularity and epsilon-similarity (Cabuk et al. 2004), corrected conditional entropy (Gianvecchio and Wang 2007), KS (exact, O(n log m)), compressibility, lag-1 autocorrelation |
| `detect` | conformal p-values from honest reference windows; refuses references too short to reach the requested alpha |
| `mitigate` | quantised release, uniform jitter, fixed schedule; proven per-packet brackets; exact integer-time reference schemes that demonstrate achievability |

## How it was verified

* **Capacity**: Blahut-Arimoto against closed forms (BSC, BEC, Z-channel, `log2(1+m)` for uniform-noise lattices), against
  30-digit `mpmath` quadrature for PAM-AWGN, random-channel property tests (bracket width, dominance over any input), and
  accelerated-versus-plain agreement.
* **Statistics**: known-answer tests (CCE of i.i.d., periodic and constant sequences, with the finite-sample bias derived and
  matched; KS against SciPy on tie-heavy cases; lag-1 autocorrelation of an AR(1) process to 0.01).
* **Detection validity**: an exact enumeration proof that the rank p-values are `{1..R+1}/(R+1)`, plus a pooled test over 60
  independent calibration sets and all six detectors.
* **Channels**: symbol error rate of the naive channel against the Q-function formula for M-PAM at 5 sigma over 600,000 symbols;
  the quantile channel's marginal against the honest CDF by KS.
* **Mitigation**: brute-force enumeration of tick increments over 2,001 phases for the quantiser upper bound; error-free
  decoding of the lattice scheme over 200,000 packets at four ratios (exact integer nanoseconds); a **negative control** in which the
  same decoder fails on more than 10 % of symbols once jitter exceeds spacing; a two-packet block channel used as a
  consistency check on the proven upper bound.

Defects found along the way, including a real off-by-one in the API, a wrong constant of mine, and a test tolerance that
ignored calibration noise, are in [`VERIFICATION_LOG.md`](VERIFICATION_LOG.md).

## Limits, stated plainly

* **Synthetic traffic.** Distribution parameters are illustrative. Whether real inference servers are as easy or as hard to
  watch is unknown. `load_ipd_csv` exists so you can find out.
* **Conformal validity needs exchangeability** between reference and test windows. Drift, a different server, or windows that
  are dependent across boundaries void it. A single warden's realised false-alarm rate also fluctuates around alpha by about
  `sqrt(alpha (1 - alpha) / R)` (0.010 at R = 520, alpha = 0.05).
* **The detectors are not hardened against adaptive attackers.** The tests establish what is undetectable in principle and what
  naive channels cost. A real attacker must first learn the honest distribution, which nothing here measures.
* **Capacity brackets are for one worst-case model**: shared clock, phase-aware sender, uniform i.i.d. payload, a single
  stream, sender-controlled extra delay up to D. Neither end is the capacity; the two-packet block computation shows the truth is
  strictly inside (1.077 per packet at D/w = 1, against a lattice rate of 1.0 and an upper bound of 1.585). The quantiser's lower end assumes a
  baseline gap that is a multiple of the tick.
* **Queueing memory is not analysed** (Anantharam and Verdu's "bits through queues" regime). FIFO release devices are covered
  by data processing; devices whose delay depends on queue state are not.
* **Blahut-Arimoto certifies the matrix you give it.** Discretisation error is O(grid step) (measured: 2 - C = 0.149, 0.075, 0.037,
  0.019 at h = 0.2, 0.1, 0.05, 0.025).
* **Fixed-schedule zero-leakage** assumes indistinguishable dummies and a queue that never overflows; packet sizes and counts are
  out of the model.
* The code and tests share an author and have had no external review.

## References

Blahut (1972), computation of channel capacity. Cabuk, Brodley and Shields, *IP covert timing channels* (CCS 2004).
Gianvecchio and Wang, *Detecting covert timing channels: an entropy-based approach* (CCS 2007). Porta et al. (2001),
corrected conditional entropy. Hopper, Langford and von Ahn, *Provably secure steganography* (CRYPTO 2002), for the
undetectability argument. Anantharam and Verdu, *Bits through queues* (1996). Askarov, Zhang and Myers, *Predictive black-box
mitigation of timing channels* (CCS 2010), the starting point for going beyond a fixed schedule.
Plan A verification supplement and get-involved page, ai-2040.com (July 2026).

## License

Apache-2.0. Copyright 2026 AnonRish.
