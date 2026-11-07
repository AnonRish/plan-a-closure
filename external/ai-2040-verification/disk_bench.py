"""
§15: sustained disk-write benchmark, run for real on this sandbox's own
storage, specifically to check for the collapse-after-burst phenomenon
Amodo measured on real NVMe (~4000 MB/s advertised -> ~70-180 MiB/s after
~12GiB). This sandbox's disk is virtualized cloud block storage, not a
consumer NVMe drive with an SLC cache to exhaust — so the exact numbers
won't match, but whether the QUALITATIVE pattern (burst, then a real,
lower sustained rate) shows up at all is worth checking directly rather
than assuming either "yes, same as Amodo" or "no, cloud storage is
different" without measuring.
"""
import os
import time
import json

def sustained_write_bench(path, total_mib, chunk_mib=128):
    buf = os.urandom(4 << 20)  # 4 MiB random buffer, reused (not the
                                 # bottleneck — disk write speed is)
    rows = []
    written = 0
    with open(path, "wb") as f:
        while written < total_mib:
            t0 = time.perf_counter()
            for _ in range(chunk_mib // 4):
                f.write(buf)
            f.flush()
            os.fsync(f.fileno())
            dt = time.perf_counter() - t0
            written += chunk_mib
            rate = chunk_mib / dt
            rows.append({"written_MiB": written, "chunk_MiB_per_s": round(rate, 1)})
            print(f"  written={written:>5} MiB  this_chunk={rate:>8.1f} MiB/s")
    os.remove(path)
    return rows


if __name__ == "__main__":
    TOTAL_MIB = 3072  # 3 GiB — as large as this sandbox's ~4.9GB free
                        # disk comfortably allows without risking filling it
    print(f"Sustained write: {TOTAL_MIB} MiB total, 128 MiB chunks, fsync'd per chunk")
    print(f"(fsync per chunk deliberately — measuring what actually reaches storage,")
    print(f" not what the page cache absorbed and will write back later)")
    rows = sustained_write_bench("/home/claude/wipe/disk_bench.tmp", TOTAL_MIB)

    first_chunk = rows[0]["chunk_MiB_per_s"]
    steady_state = [r["chunk_MiB_per_s"] for r in rows[2:]]  # skip first 2
                                                               # chunks as
                                                               # warm-up
    steady_mean = sum(steady_state) / len(steady_state) if steady_state else first_chunk
    collapse_ratio = first_chunk / steady_mean if steady_mean > 0 else 1.0

    result = {
        "total_MiB": TOTAL_MIB,
        "chunks": rows,
        "first_chunk_MiBps": first_chunk,
        "steady_state_mean_MiBps": round(steady_mean, 1),
        "collapse_ratio": round(collapse_ratio, 2),
    }
    print()
    print(json.dumps({k: v for k, v in result.items() if k != "chunks"}, indent=2))
    with open("/home/claude/wipe/disk_bench_result.json", "w") as f:
        json.dump(result, f, indent=2)
