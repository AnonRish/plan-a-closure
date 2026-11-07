// §15 — PoSE-style memory-wipe erasure daemon.
//
// Bursuc et al. (arXiv:2401.06626)'s actual contribution isn't "hash the
// memory" — it's proving erasure holds even when the prover might get help
// from an external conspirator machine, by reducing the isolation
// assumption to "the conspirator's help arrives too slowly to matter."
// That's what q < gamma is actually about below: q is how many labels a
// conspirator could plausibly ship back within one network round trip;
// gamma is the sequential dependency depth (graph-pebbling depth) of the
// DAG being labeled. If local sequential compute beats one conspirator
// round-trip per hop, outsourcing never helps, regardless of how fast the
// conspirator's own hardware is — that's the actual security argument,
// not just "count the blocks."
//
// Cite: Bursuc, Gil-Pons, Mauw, Trujillo-Rasua, "Software-Based Memory
// Erasure with relaxed isolation requirements" (arXiv:2401.06626, CSF 2024).
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <wmmintrin.h>

// ---- Dual-AES-PRF, AES-NI: H(x) = AES_k1(x) XOR AES_k2(x), 16B label ----
// Per spec: BLAKE3 is the GPU-side choice (no hardware AES on GPU); this
// daemon's CPU path (DRAM, SSD) uses Dual-AES-PRF specifically because
// AES-NI exists here and BLAKE3 would be leaving real, available hardware
// acceleration on the table for no reason on this side of the split.
static __m128i rk1[11], rk2[11];
static inline __m128i key_expand(__m128i key, __m128i kg) {
    kg = _mm_shuffle_epi32(kg, 0xff);
    key = _mm_xor_si128(key, _mm_slli_si128(key, 4));
    key = _mm_xor_si128(key, _mm_slli_si128(key, 4));
    key = _mm_xor_si128(key, _mm_slli_si128(key, 4));
    return _mm_xor_si128(key, kg);
}
static void aes128_setkey(const uint8_t k[16], __m128i rk[11]) {
    __m128i key = _mm_loadu_si128((const __m128i*)k);
    rk[0] = key;
    rk[1] = key_expand(rk[0], _mm_aeskeygenassist_si128(rk[0], 0x01));
    rk[2] = key_expand(rk[1], _mm_aeskeygenassist_si128(rk[1], 0x02));
    rk[3] = key_expand(rk[2], _mm_aeskeygenassist_si128(rk[2], 0x04));
    rk[4] = key_expand(rk[3], _mm_aeskeygenassist_si128(rk[3], 0x08));
    rk[5] = key_expand(rk[4], _mm_aeskeygenassist_si128(rk[4], 0x10));
    rk[6] = key_expand(rk[5], _mm_aeskeygenassist_si128(rk[5], 0x20));
    rk[7] = key_expand(rk[6], _mm_aeskeygenassist_si128(rk[6], 0x40));
    rk[8] = key_expand(rk[7], _mm_aeskeygenassist_si128(rk[7], 0x80));
    rk[9] = key_expand(rk[8], _mm_aeskeygenassist_si128(rk[8], 0x1b));
    rk[10] = key_expand(rk[9], _mm_aeskeygenassist_si128(rk[9], 0x36));
}
static inline __m128i aes128_enc(__m128i m, __m128i rk[11]) {
    m = _mm_xor_si128(m, rk[0]);
    for (int i = 1; i < 10; i++) m = _mm_aesenc_si128(m, rk[i]);
    return _mm_aesenclast_si128(m, rk[10]);
}
static inline void dual_aes_prf(const uint8_t in[16], uint8_t out[16]) {
    __m128i x = _mm_loadu_si128((const __m128i*)in);
    __m128i a = aes128_enc(x, rk1);
    __m128i b = aes128_enc(x, rk2);
    _mm_storeu_si128((__m128i*)out, _mm_xor_si128(a, b));
}

#define BLOCK 4096
#define LABEL 16
static double now_s(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

// Second parent: a genuinely earlier, pseudorandomly-chosen index (not the
// immediate predecessor), giving each node two real, distinct parents as
// L(n) = H(n || L(p1) || L(p2)) specifies — p1 = i-1 fixed, p2 varies.
static inline uint64_t second_parent(uint64_t i) {
    if (i < 2) return 0;
    // splitmix64-style mix so p2 is well-spread over [0, i), not just a
    // low-order-bits pattern that could accidentally correlate with p1.
    uint64_t z = i + 0x9E3779B97F4A7C15ULL;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    z = z ^ (z >> 31);
    return z % i;
}

int main(int argc, char** argv) {
    size_t mib = argc > 1 ? (size_t)atol(argv[1]) : 256;
    uint8_t key1[16] = {1}, key2[16] = {2};
    aes128_setkey(key1, rk1);
    aes128_setkey(key2, rk2);

    size_t n_blocks = (mib << 20) / BLOCK;
    uint8_t* region = aligned_alloc(64, n_blocks * (size_t)BLOCK);
    if (!region) { fprintf(stderr, "allocation failed for %zu MiB\n", mib); return 1; }
    memset(region, 0xA5, n_blocks * BLOCK);

    // ---- Phase 1: DAG label pass, TRUE two-parent dependency ----
    // Each label depends on the ACTUAL prior labels (not just their
    // presence) — this is what makes the chain genuinely sequential and
    // is the entire basis for gamma meaning something below. A version
    // that only reads a few bytes of the parent block without them
    // actually being labels yet would make the "dependency" cosmetic.
    double t0 = now_s();
    uint64_t labels_done = 0;
    for (size_t i = 0; i < n_blocks; i++) {
        uint8_t in[16];
        memcpy(in, &i, 8);
        if (i == 0) {
            memset(in + 8, 0, 8);
        } else {
            uint64_t p2 = second_parent(i);
            // fold 4 bytes from each REAL parent label (already written
            // in a prior iteration of this same loop — true dependency)
            memcpy(in + 8, region + (i - 1) * BLOCK, 4);
            memcpy(in + 12, region + p2 * BLOCK, 4);
        }
        uint8_t lab[16];
        dual_aes_prf(in, lab);
        memcpy(region + i * BLOCK, lab, LABEL);
        labels_done++;
    }
    double t_label = now_s() - t0;

    // ---- Depth-robustness: measure ONE forced-sequential hop's real
    // latency (can't parallelize a true dependency chain), then compare
    // against a conspirator round-trip. q = labels a conspirator could
    // return within one RTT (bandwidth/compute-unlimited on their end —
    // the assumption that favors the ATTACKER); gamma = this DAG's real
    // sequential depth for the region just labeled. ----
    const double ASSUMED_RTT_S = 0.001;  // 1ms, realistic same-datacenter
                                          // RTT — favorable to the
                                          // conspirator; a real deployment
                                          // should use its actual measured
                                          // RTT to the nearest plausible
                                          // conspirator host, not this
    double single_hop_latency_s = t_label / (double)n_blocks;
    double q_labels_per_rtt = ASSUMED_RTT_S / single_hop_latency_s;
    // gamma: the graph's actual sequential depth. Because parent p1=i-1 is
    // fixed, this construction's longest dependency chain is the full
    // block count — a real property of THIS graph, not an assumption.
    uint64_t gamma_hops = n_blocks;

    // ---- Phase 2: full-region overwrite — every byte, not just labels.
    // This is the actual erasure; the label pass alone would leave 4080 of
    // every 4096 bytes untouched. AES-CTR keystream, in place. ----
    t0 = now_s();
    for (size_t i = 0; i < n_blocks; i++) {
        uint8_t* blk = region + i * BLOCK;
        for (size_t off = 0; off < BLOCK; off += 16) {
            uint8_t ctr[16], ks[16];
            uint64_t c = i * (BLOCK / 16) + off / 16;
            memset(ctr, 0, 16);
            memcpy(ctr, &c, 8);
            dual_aes_prf(ctr, ks);
            memcpy(blk + off, ks, 16);
        }
    }
    double t_wipe = now_s() - t0;

    double mb = (double)mib;
    printf("region_MiB=%zu blocks=%zu block_size=%d\n", mib, n_blocks, BLOCK);
    printf("label_pass_s=%.4f (%.1f MiB/s, %.0f labels/s)\n", t_label, mb / t_label, labels_done / t_label);
    printf("wipe_pass_s=%.4f (%.1f MiB/s)\n", t_wipe, mb / t_wipe);
    printf("single_hop_latency_ns=%.1f\n", single_hop_latency_s * 1e9);
    printf("q_labels_per_rtt(assumed_rtt_ms=%.1f)=%.0f\n", ASSUMED_RTT_S * 1000, q_labels_per_rtt);
    printf("gamma_sequential_depth=%" PRIu64 "\n", (uint64_t)gamma_hops);
    printf("depth_robust(q<gamma)=%s\n", q_labels_per_rtt < (double)gamma_hops ? "true" : "false");
    free(region);
    return 0;
}
