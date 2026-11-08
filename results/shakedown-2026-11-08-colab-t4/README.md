# Colab T4 shakedown, 8 November 2026 (plan-a-closure 0.5.4)

The first run of `closure tier0 --confirm-hardware` on real hardware: a free Google Colab Tesla T4, NVML only, no
independent meter. It stopped at `hw-selftest` (r2 = 0.719, needs > 0.9). Write-up and diagnosis:
[docs/DEVIATIONS.md](../../docs/DEVIATIONS.md) section 1.

| file | what it is |
| --- | --- |
| `tier0_bundle.tar.gz` | the bundle as returned, sha256 `2fd41f34f679dc061b899e89bfce1c9fcdc62fbf2840f89205561fa2ec409a5f` |
| `extracted/` | its contents: `SUMMARY.md` and the step logs |
| `model/repro_t4.py` | the model-in-the-loop reproduction: the real load generator, window logic and hw-selftest fit, with only the GPU replaced by a timing and power model |
| `model/*.json` | its outputs (below) |

| model run | code | r2 | units per window at 25% and 100% load | result |
| --- | --- | ---: | --- | --- |
| `old_main.json` | 0.5.4, exact meter | 0.838 | not reported by 0.5.4 (both about 1.85) | fail |
| `old_jit.json` | 0.5.4, 25% unit-time jitter, 4 W power ripple | 0.769 | not reported by 0.5.4 | fail |
| observed on the T4 | 0.5.4 | 0.719 | | fail |
| `new_t4.json` | 0.5.5, fp16 as on a T4 | 1.000 | 39.9 and 155.2 | pass |
| `new_t4_jit.json` | 0.5.5, fp16, jitter and ripple | 0.998 | 42.3 and 151.1 | pass |
| `new_bf16.json` | 0.5.5, bf16 kept (sizing alone) | 1.000 | 29.9 and 115.7 | pass |

To rerun (each run takes about 2.5 minutes and needs CPU torch):

```
git worktree add ../pac-0.5.4 579a533          # the code that ran on the T4
python -I results/shakedown-2026-11-08-colab-t4/model/repro_t4.py --src ../pac-0.5.4/src
python -I results/shakedown-2026-11-08-colab-t4/model/repro_t4.py --src src --turing
```

A model reproducing the failure does not show what a T4 will do on 0.5.5. The next Colab run does, and it is appended
to docs/DEVIATIONS.md whatever it shows.
