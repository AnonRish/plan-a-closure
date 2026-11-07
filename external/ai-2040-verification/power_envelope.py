"""§20: corrected power-envelope calculation, real H100 SXM figures, checked
arithmetic (a separate document shared with me got this wrong: as literally
written, its formula computed to 7.0 MW while claiming 10.0 MW)."""

GPU_TDP_W = 700  # H100 SXM, confirmed via NVIDIA's own HGX H100 PCF summary
                  # datasheet (8x700W = 5600W baseboard figure)
EFFECTIVE_W_PER_GPU = 762.5  # includes host/CPU/storage/NIC overhead, from a
                              # real cited 8-GPU-node figure (~6.1kW/8 GPUs)
PUE = 1.15  # modern hyperscale-efficient range is 1.1-1.3 per multiple
             # independent sources; 1.15 sits inside that range

def max_supportable_gpus(intertie_mw, pue=PUE, w_per_gpu=EFFECTIVE_W_PER_GPU):
    return int((intertie_mw * 1e6 / pue) / w_per_gpu)

def required_facility_mw(n_gpus, pue=PUE, w_per_gpu=EFFECTIVE_W_PER_GPU):
    return (n_gpus * w_per_gpu * pue) / 1e6

if __name__ == "__main__":
    n_declared = 10000
    required = required_facility_mw(n_declared)
    print(f"Declared: {n_declared:,} H100 SXM GPUs")
    print(f"Required facility draw: {required:.3f} MW (at {EFFECTIVE_W_PER_GPU}W/GPU effective, PUE {PUE})")
    for intertie in [5, 8, 10, 12]:
        max_gpus = max_supportable_gpus(intertie)
        print(f"  {intertie} MW intertie -> max supportable: {max_gpus:,} GPUs "
              f"({'CONSISTENT' if max_gpus >= n_declared else 'IMPOSSIBLE, declared count exceeds physical capacity'})")
