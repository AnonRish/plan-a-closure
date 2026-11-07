"""A fake `nvidia-smi` for rehearsals (tests/test_hw_rehearsal.py installs it on PATH as `nvidia-smi`).

Understands what plan-a-closure uses: `-i <index|UUID>` with `-lgc a,b`, `-rgc` or `-pl W`. It keeps the locked clock
and power limit per GPU in FAKEGPU_STATE (read by the fake pynvml) and appends every call to FAKEGPU_LOG.
FAKEGPU_DENY=1 answers like a non-root user; FAKEGPU_LGC_NOOP=1 accepts -lgc but changes nothing, as some virtual
machines do.
"""
import json
import os
import sys

DEFAULT_W, MIN_W, MAX_W = 700.0, 200.0, 700.0


def main(args) -> int:
    log = os.environ.get("FAKEGPU_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(" ".join(args) + "\n")
    if "-i" not in args:
        print("fake nvidia-smi: this fake needs -i <gpu>")
        return 2
    ident = args[args.index("-i") + 1]
    n = int(os.environ.get("FAKEGPU_COUNT", "2"))
    uuids = {f"GPU-fa4e0000-0000-4000-8000-{i:012d}": i for i in range(n)}
    if ident in uuids:
        gi = uuids[ident]
    elif ident.isdigit() and int(ident) < n:
        gi = int(ident)
    else:
        print(f"No devices were found matching {ident}")
        return 6
    if os.environ.get("FAKEGPU_DENY") == "1" and any(a in args for a in ("-lgc", "-rgc", "-pl")):
        print(f"Unable to apply the change for GPU 00000000:{0x18 + gi:02X}:00.0: Insufficient Permissions")
        return 4
    path = os.environ["FAKEGPU_STATE"]
    st = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            st = json.load(f)
    g = st.setdefault(str(gi), {"clock": None, "limit_w": DEFAULT_W})
    if "-lgc" in args:
        a, b = args[args.index("-lgc") + 1].split(",")
        if os.environ.get("FAKEGPU_LGC_NOOP") == "1":
            print(f"Setting locked GPU clocks is not supported for GPU {gi}. Treating as warning and moving on.")
            return 0
        g["clock"] = int(a)
        print(f'GPU clocks set to "(gpcclk {a}, {b})" for GPU {gi}')
    elif "-rgc" in args:
        g["clock"] = None
        print(f"All done. (GPU {gi})")
    elif "-pl" in args:
        w = float(args[args.index("-pl") + 1])
        if not MIN_W <= w <= MAX_W:
            print(f"Provided power limit {w:.2f} W is not a valid power limit, which should be between {MIN_W} and {MAX_W} W")
            return 2
        g["limit_w"] = w
        print(f"Power limit for GPU {gi} was set to {w:.2f} W.")
    else:
        print("fake nvidia-smi: unsupported command")
        return 2
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st, f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
