"""
§25: Proof-of-Learning (PoL), the real named mechanism here -- Jia et al.
(2021): the prover periodically logs weight snapshots and the data used
between them; a verifier replays sampled segments from a logged snapshot
and checks whether it arrives at the next one. This is the SAME shape as
everything else in this document (verifier-controlled sampling, verifier-
side recomputation, a real check rather than a signed assertion) applied
one level up: not a forward pass, a whole training SEGMENT.

Also real: Fang et al., "Proof-of-learning is currently more broken than
you think" (EuroS&P 2023) -- a serious, published critique. This file
doesn't just cite that title and move on; it tries to find the actual
tension the critique is about, honestly, by testing both a real attack
AND a case that isn't an attack at all.

What's genuinely testable in this sandbox: the replay mechanism itself,
on a tiny real model, with real gradient steps. What ISN'T testable here
and is stated as such: whether this holds up at real training scale, real
training duration, and real cross-hardware determinism variance --
exactly the §7 problem, now mattering over weeks of compute instead of
one forward pass.
"""
import numpy as np
import hashlib
import time
from model import TinyCharLM, softmax
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tamper_log import TamperEvidentLog

CONTEXT_LEN = 8
EMBED_DIM = 32
HIDDEN_DIM = 128
BATCH_SIZE = 256
LR = 0.05


def load_data():
    with open("shakespeare.txt") as f:
        text = f.read()
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    data = np.array([stoi[c] for c in text], dtype=np.int64)
    return data, stoi


def make_segment_batches(data, seed, n_steps, batch_size=BATCH_SIZE):
    """Deterministically regenerate the exact batch sequence for one
    segment from its seed alone -- this is what lets a verifier replay a
    segment without the prover having to log every individual batch
    index, the same 'seed instead of raw content' economy §1/§5 already
    use for decode sampling, applied here to data selection instead."""
    rng = np.random.default_rng(seed)
    n = len(data) - CONTEXT_LEN - 1
    batches = []
    for _ in range(n_steps):
        idx = rng.integers(0, n, size=batch_size)
        ctx = np.stack([data[i:i + CONTEXT_LEN] for i in idx])
        tgt = data[idx + CONTEXT_LEN]
        batches.append((ctx, tgt))
    return batches


def checkpoint_hash(model):
    """What actually gets logged and compared. At this sandbox's toy
    scale the weights themselves (a few hundred KB) could be logged
    directly; a real deployment's checkpoints run to hundreds of
    gigabytes, so a hash standing in for the weights is what the real
    mechanism needs, and it's what's tested here rather than the easier
    (and unrealistic) direct-comparison version."""
    buf = b"".join(np.ascontiguousarray(p).tobytes() for p in model.params())
    return hashlib.sha256(buf).hexdigest()


def run_segment(model, data, seed, n_steps, lr=LR):
    """One segment of REAL training: actual forward, actual backward,
    actual weight updates -- not simulated, not interpolated."""
    batches = make_segment_batches(data, seed, n_steps)
    for ctx, tgt in batches:
        logits, cache = model.forward(ctx)
        probs = softmax(logits)
        model.backward(cache, probs, tgt, lr)
    return model


def clone_model(model):
    import copy
    return copy.deepcopy(model)


class ProverLog:
    """The prover's own segment-by-segment training log -- §21b's
    construction reused a SIXTH time in this document, now for training
    provenance instead of an inference-verification report, a tap
    registry, a workload approval, or a release record."""
    def __init__(self, key: Ed25519PrivateKey):
        self.log = TamperEvidentLog(key)

    def log_segment(self, seg_idx, start_hash, end_hash, seed, n_steps, lr):
        return self.log.append({
            "event": "segment", "seg_idx": seg_idx,
            "start_hash": start_hash, "end_hash": end_hash,
            "seed": seed, "n_steps": n_steps, "lr": lr,
        })


def verify_segment(claimed_start_model, claimed_seed, claimed_n_steps, claimed_end_hash, data, lr=LR):
    """The verifier's whole job: reload the claimed starting point (in a
    real deployment, checked against its OWN hash first -- assumed
    already validated here since it's the prior segment's already-
    verified end state), independently replay the claimed number of
    steps with the claimed seed, and check whether the result matches
    the claimed end state. No trust in the prover's claimed end_hash
    beyond what this recomputation confirms."""
    model = clone_model(claimed_start_model)
    run_segment(model, data, claimed_seed, claimed_n_steps, lr)
    recomputed_hash = checkpoint_hash(model)
    return recomputed_hash == claimed_end_hash, recomputed_hash, model


if __name__ == "__main__":
    data, stoi = load_data()
    N_SEGMENTS = 8
    STEPS_PER_SEGMENT = 400

    print("=" * 92)
    print(f"1. Honest prover: {N_SEGMENTS} real segments x {STEPS_PER_SEGMENT} real gradient steps each")
    print("=" * 92)
    prover_key = Ed25519PrivateKey.generate()
    prover_log = ProverLog(prover_key)

    model = TinyCharLM(vocab_size=len(stoi), context_len=CONTEXT_LEN, embed_dim=EMBED_DIM, hidden_dim=HIDDEN_DIM, seed=1)
    checkpoints = [clone_model(model)]
    t0 = time.time()
    for seg in range(N_SEGMENTS):
        start_hash = checkpoint_hash(checkpoints[-1])
        seed = 1000 + seg
        seg_model = clone_model(checkpoints[-1])
        run_segment(seg_model, data, seed, STEPS_PER_SEGMENT)
        end_hash = checkpoint_hash(seg_model)
        prover_log.log_segment(seg, start_hash, end_hash, seed, STEPS_PER_SEGMENT, LR)
        checkpoints.append(seg_model)
        print(f"  segment {seg}: {start_hash[:12]}... -> {end_hash[:12]}...")
    print(f"  ({time.time()-t0:.1f}s for {N_SEGMENTS * STEPS_PER_SEGMENT} total real gradient steps)")

    ok, msg = prover_log.log.verify_integrity()
    print(f"  Prover's own log integrity: {ok} ({msg})")
    assert ok

    print()
    print("=" * 92)
    print("2. Verifier samples ONE random segment (this document's own recurring principle --")
    print("   §1's budget-limited sampling, applied to training segments instead of packets)")
    print("=" * 92)
    rng = np.random.default_rng(55)
    sampled_seg = int(rng.integers(0, N_SEGMENTS))
    entry = prover_log.log.entries[sampled_seg + 1].payload  # +1 for genesis entry
    ok, recomputed, _ = verify_segment(checkpoints[sampled_seg], entry["seed"], entry["n_steps"], entry["end_hash"], data)
    print(f"  Sampled segment {sampled_seg}: claimed_end={entry['end_hash'][:12]}...  recomputed={recomputed[:12]}...")
    print(f"  Independent replay matches claimed checkpoint: {ok}")
    assert ok, "an honest segment must replay to a bit-exact match on the same hardware/software"
    print("PASS: same hardware, same code, same seed -> bit-exact reproduction, not just 'close'.")
    print("(This is the SAME determinism §7 found requires real engineering across different")
    print("hardware or even different batch shapes -- it holding here for free is a same-machine,")
    print("same-run property, not something a real cross-facility deployment gets automatically.)")

    print()
    print("=" * 92)
    print("3. THE ATTACK: prover claims a full segment's compute, actually does a fraction of it")
    print("=" * 92)
    cheat_seg = 3
    real_start = checkpoints[cheat_seg]
    honest_seed = 1000 + cheat_seg
    cheap_model = clone_model(real_start)
    CHEAP_STEPS = STEPS_PER_SEGMENT // 8  # spends 1/8 the claimed compute
    run_segment(cheap_model, data, honest_seed, CHEAP_STEPS)
    forged_end_hash = checkpoint_hash(cheap_model)  # prover reports THIS as if
                                                       # STEPS_PER_SEGMENT had run
    ok, recomputed, _ = verify_segment(real_start, honest_seed, STEPS_PER_SEGMENT, forged_end_hash, data)
    print(f"  Claimed: {STEPS_PER_SEGMENT} steps, seed={honest_seed}, forged_end={forged_end_hash[:12]}...")
    print(f"  Verifier's real {STEPS_PER_SEGMENT}-step replay: {recomputed[:12]}...")
    print(f"  Match: {ok} (must be False -- {CHEAP_STEPS}/{STEPS_PER_SEGMENT} of the claimed compute was never spent)")
    assert not ok
    print("PASS: claiming more compute than was actually spent is caught -- the verifier's replay")
    print("cost the SAME compute the prover claimed, which is the real economics DiFR-style")
    print("recomputation always has (§1's C-fraction budget), now paid in training steps.")

    print()
    print("=" * 92)
    print("4. THE HONEST TENSION: a genuinely different but equally real training path")
    print("=" * 92)
    alt_seg = 3
    alt_start = checkpoints[alt_seg]
    alt_seed = 1000 + alt_seg + 500  # a DIFFERENT seed -- different data order,
                                        # SAME number of real steps, SAME compute
                                        # actually spent, still legitimate SGD
    alt_model = clone_model(alt_start)
    run_segment(alt_model, data, alt_seed, STEPS_PER_SEGMENT)
    alt_hash = checkpoint_hash(alt_model)
    original_claimed_hash = prover_log.log.entries[alt_seg + 1].payload["end_hash"]
    print(f"  Original logged path (seed={1000+alt_seg}):  end_hash={original_claimed_hash[:12]}...")
    print(f"  Alternate REAL path (seed={alt_seed}, same n_steps, same real compute): end_hash={alt_hash[:12]}...")
    print(f"  Hashes match: {alt_hash == original_claimed_hash} (this is the actual tension, not a bug)")
    print()
    print("This is real, full compute spent honestly, and it does NOT reproduce the originally")
    print("logged checkpoint -- because SGD's trajectory depends on data ORDER, not just which")
    print("data and how many steps. Exact-hash replay verification, as tested above, only")
    print("accepts the ONE specific path the prover committed to at logging time. That's not a")
    print("weakness of this implementation -- it's the actual content of Fang et al.'s published")
    print("critique of proof-of-learning: verifying 'was this EXACT trajectory produced' is")
    print("stricter than the real question ('was genuine, uncompromised compute spent'), and the")
    print("gap between those two questions is exactly where a more sophisticated forger, not")
    print("tested here, would look for room to spend LESS real compute while still landing on")
    print("SOME trajectory that satisfies whatever check is actually being run.")
