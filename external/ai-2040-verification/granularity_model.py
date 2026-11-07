"""
§14: assurance vs. packet granularity, on §1's real formula.

Starting point: Kimi's assurance_model.py (code/s14_granularity in the
uploaded zip) got the structure right — four stages, real dependencies,
§1's formula, a real plot. What it computes is C-for-99%-detection as a
function of N_fake alone, which comes out IDENTICAL at every granularity
stage (verified by actually running it) — because N_fake there is "fake
things per day," entered as the same constant regardless of what a
"thing" is. That's the part granularity is actually supposed to change:
the same underlying violation, measured in FINER units, IS a bigger
N_fake, which is the entire mechanism by which finer granularity is
supposed to buy cheaper detection. This version computes that connection
explicitly instead of holding N_fake constant across stages.
"""
import numpy as np
import json

# Reference deployment, grounded in this document's own measured numbers
# rather than fresh assumptions where they already exist.
REQ_PER_SEC = 1000
TOKENS_PER_REQ = 512
FRAMES_PER_REQ = 40          # ~1500B frames per streamed request, matches
                              # §2/§4's own frame-size assumptions
FORWARD_PASSES_PER_TOKEN = 1  # one packet-of-evidence per generated token
                              # at the finest stage modeled here
DAY_SECONDS = 86400

# §2's real measured software ceiling (per core, 1500B frames): 7.35 Gbps.
# §4's real measured hash-only ceiling (per core, 1500B): 10.02 Gbps.
# Used below to convert "packets recomputed per day" into "cores needed",
# not just an abstract fraction C.
S2_GBPS_PER_CORE_1500B = 7.35
S4_HASH_GBPS_PER_CORE_1500B = 10.02
BYTES_PER_FRAME = 1500

def C_for_target(p_target, n_fake):
    """Exact form, not the small-C approximation — matches §1's own
    footnote that the approximation breaks down at small N_fake."""
    if n_fake <= 0:
        return 1.0
    return min(1.0, 1 - (1 - p_target) ** (1 / n_fake))


# Granularity stages: what does "one packet of evidence" cover, and how
# many packets does ONE FIXED VIOLATION span at each stage. The violation
# modeled: a prover substitutes a dishonest model for ONE FULL REQUEST
# (512 tokens, 40 frames) — held constant in real-world size across every
# row, which is the actual point.
stages = {
    "S0_request_level (§2 floor)": {
        "packets_per_violation": 1,                    # one request = one packet
        "packets_per_day": REQ_PER_SEC * DAY_SECONDS,
        "depends_on": ["§2"],
        "reproducibility_burden": 1.0,                  # baseline
    },
    "S1_frame_level (§2+§8)": {
        "packets_per_violation": FRAMES_PER_REQ,        # one violation now
                                                          # spans 40 packets
        "packets_per_day": REQ_PER_SEC * FRAMES_PER_REQ * DAY_SECONDS,
        "depends_on": ["§2", "§8"],                      # needs §8's reorder
                                                          # fix to make frame-
                                                          # level evidence
                                                          # trustworthy at all
        "reproducibility_burden": 1.15,                  # §8's real finding:
                                                          # reorder buffer adds
                                                          # bookkeeping, not a
                                                          # new bottleneck
    },
    "S2_frame_level_sampled (§2+§3+§4+§8)": {
        "packets_per_violation": FRAMES_PER_REQ,
        "packets_per_day": REQ_PER_SEC * FRAMES_PER_REQ * DAY_SECONDS,
        "depends_on": ["§2", "§3", "§4", "§8"],
        "reproducibility_burden": 1.15,                  # same evidence unit
                                                          # as S1; §3/§4 change
                                                          # WHO pays bandwidth,
                                                          # not what a packet is
    },
    "S3_token_level (§2+§3+§8+§22-UNSOLVED)": {
        "packets_per_violation": TOKENS_PER_REQ,         # one violation now
                                                          # spans 512 packets
        "packets_per_day": REQ_PER_SEC * TOKENS_PER_REQ * DAY_SECONDS,
        "depends_on": ["§2", "§3", "§8", "§22-UNSOLVED"],
        "reproducibility_burden": 3.0,                   # backend visibility:
                                                          # genuinely unsolved,
                                                          # not just "harder"
    },
}

TARGET_P = 0.99
results = {}
for name, s in stages.items():
    n_fake = s["packets_per_violation"]  # ONE violation, measured in this
                                          # stage's own units
    c_required = C_for_target(TARGET_P, n_fake)
    packets_recomputed_per_day = c_required * s["packets_per_day"]
    bytes_recomputed_per_day = packets_recomputed_per_day * BYTES_PER_FRAME
    gbps_recomputed = bytes_recomputed_per_day * 8 / DAY_SECONDS / 1e9
    cores_needed_s2 = gbps_recomputed / S2_GBPS_PER_CORE_1500B
    cores_needed_s4_hash_only = gbps_recomputed / S4_HASH_GBPS_PER_CORE_1500B

    results[name] = {
        "packets_per_violation_N_fake": n_fake,
        "C_required_for_99pct": c_required,
        "total_packets_per_day": s["packets_per_day"],
        "packets_recomputed_per_day": packets_recomputed_per_day,
        "recompute_load_gbps": gbps_recomputed,
        "cores_needed_full_recompute_§2": cores_needed_s2,
        "cores_needed_hash_only_§4": cores_needed_s4_hash_only,
        "reproducibility_burden_multiplier": s["reproducibility_burden"],
        "effective_cores_incl_burden": cores_needed_s2 * s["reproducibility_burden"],
        "depends_on": s["depends_on"],
    }

print(json.dumps(results, indent=2))
with open("granularity_model.json", "w") as f:
    json.dump(results, f, indent=2)
