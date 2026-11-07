"""packet-forge command line."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from typing import List, Optional

from . import __version__
from .analyze import FAIL_KINDS, analyze_pcap
from .corpus import all_cases, build_manifest, expected_for_case, get_case, write_corpus
from .model import DEFAULT_POLICIES, POLICIES
from .pcap import LINKTYPE_ETHERNET, LINKTYPE_RAW, PcapError


def _print_report(rep, path: str, out) -> None:
    print("capture %s: %d frame(s), %d TCP segment(s), checksums: %s" % (path, rep.frames, rep.tcp_segments,
                                                                       rep.checksum_mode), file=out)
    for n in rep.frame_notes:
        print("  note %s: %s (frames %s)" % (n.kind, n.detail, ",".join(map(str, n.frames[:10]))), file=out)
    for d in rep.directions:
        print("flow %s  claims=%d bytes=%d syn=%s fin=%s holes=%s" % (
            d.flow, d.claims, d.bytes_claimed, "yes" if d.syn_seen else "no",
            d.fin_offset if d.fin_offset is not None else "-", d.holes or "none"), file=out)
        for name, s in d.streams.items():
            print("  stream[%-6s] %5d B  sha256=%s %s" % (name, s.length, s.sha256[:16],
                                                          "complete" if s.complete else "INCOMPLETE"), file=out)
        if d.policy_divergent:
            print("  policies DISAGREE: the reassembled stream depends on the receiver's overlap rules", file=out)
        for c in d.conflicts:
            frames_ = ",".join(str(x["frame"]) for x in c.claims)
            late = (" late-after-ACK frames=%s" % ",".join(map(str, c.late_after_ack))) if c.late_after_ack else ""
            print("  CONFLICT stream bytes [%d,%d): %d distinct value(s), claims from frames %s%s" % (
                c.start, c.end, c.distinct_values, frames_, late), file=out)
            if c.hint:
                print("    hint: %s" % c.hint, file=out)
        for a in d.anomalies:
            print("  anomaly %-16s frames=%s  %s" % (a.kind, ",".join(map(str, a.frames[:10])), a.detail), file=out)
    print("verdict: %s" % ("AMBIGUOUS" if rep.failing() else "CLEAN"), file=out)


def cmd_check(a) -> int:
    pols = tuple(a.policies.split(",")) if a.policies else DEFAULT_POLICIES
    for p in pols:
        if p not in POLICIES:
            print("unknown policy %r (have %s)" % (p, ", ".join(POLICIES)), file=sys.stderr)
            return 2
    rc = 0
    for path in a.pcap:
        try:
            rep = analyze_pcap(path, pols, "accept" if a.no_checksum else "verify", include_hex=a.streams)
        except (OSError, PcapError) as e:
            print("%s: %s" % (path, e), file=sys.stderr)
            return 2
        if a.json:
            json.dump(rep.to_dict(), sys.stdout, indent=1)
            print()
        else:
            _print_report(rep, path, sys.stdout)
        rc = max(rc, 1 if rep.failing(a.fail_on.split(",") if a.fail_on else FAIL_KINDS) else 0)
    return rc


def cmd_list(a) -> int:
    for c in all_cases():
        print("%-34s %-9s %s" % (c.id, c.category, c.title))
    return 0


def cmd_show(a) -> int:
    c = get_case(a.case)
    print("%s (%s)\n%s\n" % (c.id, c.category, c.description))
    for e in c.events:
        print("  ", e)
    exp = expected_for_case(c)
    print("\nconflict ranges:", exp["conflict_ranges"], "| anomalies:", exp["anomalies"],
          "| ambiguous:", exp["ambiguous"], "| policies disagree:", exp["policy_divergent"])
    for n, s in exp["streams"].items():
        print("  %-7s %r%s" % (n, bytes.fromhex(s["hex"]), "" if s["complete"] else "  (incomplete)"))
    return 0


def cmd_generate(a) -> int:
    lt = LINKTYPE_RAW if a.raw else LINKTYPE_ETHERNET
    m = write_corpus(a.outdir, ipv6=a.ipv6, vlans=tuple(a.vlan or ()), linktype=lt, nano=a.nano)
    print("wrote %d cases + all-cases.pcap + manifest.json + SHA256SUMS to %s" % (len(m["cases"]), a.outdir))
    return 0


def cmd_verify_corpus(a) -> int:
    """Regenerate the corpus and require byte-identical output; then re-derive every case's expectations
    through the pcap -> parser -> reassembler pipeline and compare with the manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        write_corpus(tmp)
        bad = 0
        for name in sorted(os.listdir(tmp)):
            ours, theirs = os.path.join(tmp, name), os.path.join(a.dir, name)
            if not os.path.exists(theirs) or open(ours, "rb").read() != open(theirs, "rb").read():
                print("DIFFERS  %s" % name)
                bad += 1
        manifest = json.load(open(os.path.join(a.dir, "manifest.json")))
        for e in manifest["cases"]:
            rep = analyze_pcap(os.path.join(a.dir, e["pcap"]), include_hex=True)
            d = next(x for x in rep.directions if x.flow.startswith(e["client"] + ">"))
            exp = e["expected"]
            got = {"conflict_ranges": [[c.start, c.end] for c in d.conflicts],
                   "streams": {k: v.hex for k, v in d.streams.items()}}
            want = {"conflict_ranges": exp["conflict_ranges"], "streams": {k: v["hex"] for k, v in exp["streams"].items()}}
            kinds = set(d.kinds()) | {n.kind for n in rep.frame_notes}
            if got != want or kinds != set(exp["anomalies"]):
                print("MISMATCH %s" % e["id"])
                bad += 1
    print("corpus verified" if not bad else "%d problem(s)" % bad)
    return 1 if bad else 0


def cmd_normalize(a) -> int:
    from .normalize import normalize_pcap
    st = normalize_pcap(a.src, a.dst, a.policy, "accept" if a.no_checksum else "verify")
    print("%d -> %d frames; %d payload(s) rewritten, %d bad-checksum frame(s) dropped" % (
        st.frames_in, st.frames_out, st.rewritten, st.dropped_bad_checksum))
    return 0


def cmd_kernel(a) -> int:
    from . import kernel_replay as kr
    why = kr.kernel_available()
    if why:
        print("kernel replay unavailable: %s" % why, file=sys.stderr)
        return 2
    from .corpus import permutations
    out = {}
    with kr.KernelBench() as bench:
        cases = [c for c in all_cases() if c.handshake]
        res = kr.kernel_verify(cases, bench)
        out = {"kernel": bench.kernel, "cases": res, "known_deviations": kr.KNOWN_DEVIATIONS}
        bad = [k for k, v in res.items() if not v["linux_model_matches"]]
        print("kernel %s: `linux` model reproduces the kernel on %d/%d corpus cases" % (bench.kernel, len(res) - len(bad), len(res)))
        for k in bad:
            print("  differs: %-30s %s" % (k, kr.KNOWN_DEVIATIONS.get(k, "UNEXPLAINED")))
        if a.permutations:
            ok = n = 0
            for base in cases:
                for c in permutations(base):
                    if any(s.frag for s in c.segs()):
                        continue
                    obs = bench.run_case(c)
                    n += 1
                    ok += bytes.fromhex(expected_for_case(c)["streams"]["linux"]["hex"]) == obs.data
            out["permutations"] = {"replayed": n, "model_matches": ok}
            print("arrival-order permutations: model reproduces the kernel on %d/%d" % (ok, n))
        if a.fuzz:
            fz = kr.kernel_fuzz(a.fuzz, a.seed, bench)
            out["fuzz"] = fz
            print("random scenarios (seed %d): %s of %d reproduced by each policy" % (a.seed, fz["agree"], fz["scenarios"]))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, indent=1, sort_keys=True)
            f.write("\n")
    return 0


def cmd_taps(a) -> int:
    from .taps import TAPS, run_tap, score
    manifest = json.load(open(os.path.join(a.dir, "manifest.json")))
    kernel = None
    if a.kernel:
        kernel = json.load(open(a.kernel))["cases"]
    print("%-16s %7s  %s" % ("tap", "pass", "failing cases (first few)"))
    for name, tap in TAPS.items():
        sc = score(run_tap(tap, manifest, a.dir), manifest, kernel)
        failing = [k for k, r in sc["cases"].items() if not r["pass"]]
        fid = (" | stream==Linux bytes %d/%d" % (sc["fidelity_matches"], sc["fidelity_total"])) if kernel else ""
        print("%-16s %3d/%-3d%s  %s" % (name, sc["passed"], sc["total"], fid, ", ".join(failing[:3]) + (" ..." if len(failing) > 3 else "")))
    return 0


def cmd_score(a) -> int:
    from .taps import TapVerdict, score
    manifest = json.load(open(os.path.join(a.dir, "manifest.json")))
    raw = json.load(open(a.results))
    verdicts = {k: TapVerdict(bytes.fromhex(v.get("stream_hex", "")), bool(v.get("flagged", False))) for k, v in raw.items()}
    kernel = json.load(open(a.kernel))["cases"] if a.kernel else None
    sc = score(verdicts, manifest, kernel)
    for k, r in sc["cases"].items():
        if not r["pass"]:
            print("FAIL %-34s %s" % (k, {x: y for x, y in r.items() if x != "pass"}))
    print("passed %d/%d" % (sc["passed"], sc["total"]) + (
        "; stream equals the Linux receiver's bytes on %d/%d" % (sc["fidelity_matches"], sc["fidelity_total"]) if kernel else ""))
    return 0 if sc["passed"] == sc["total"] else 1


def cmd_tap_reader(a) -> int:
    """Run the corpus through the tap_reader Rust crate and compare with the live-kernel observations."""
    from . import tap_reader as tr
    manifest = json.load(open(os.path.join(a.dir, "manifest.json")))
    kernel = json.load(open(a.kernel))["cases"]
    try:
        binary = tr.build_adapter(a.adapter_dir)
    except (RuntimeError, OSError) as e:
        print("cannot build the adapter: %s" % e, file=sys.stderr)
        return 2
    out = {}
    for mode in (["asis", "trim"] if a.mode == "both" else [a.mode]):
        res = tr.run_adapter(binary, manifest, a.dir, mode)
        differs = sorted(k for k in kernel if res[k]["stream"].hex() != kernel[k]["observed_hex"])
        print("mode %-4s: delivered stream equals the Linux receiver's bytes on %d/%d cases" % (
            mode, len(kernel) - len(differs), len(kernel)))
        if mode == "trim" or a.verbose:
            for k in differs:
                print("   differs %-30s tap_reader=%r kernel=%r gap_open=%s" % (
                    k, res[k]["stream"][:28], bytes.fromhex(kernel[k]["observed_hex"])[:28], res[k]["gap_open"]))
        out[mode] = {"differs": differs}
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="packet-forge", description=__doc__)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="reassemble a capture, flag conflicting overlaps and anomalies")
    c.add_argument("pcap", nargs="+")
    c.add_argument("--policies", help="comma list (default %s)" % ",".join(DEFAULT_POLICIES))
    c.add_argument("--json", action="store_true")
    c.add_argument("--streams", action="store_true", help="include reassembled stream bytes (hex) in --json")
    c.add_argument("--no-checksum", action="store_true", help="accept segments with bad checksums")
    c.add_argument("--fail-on", help="comma list of anomaly kinds that make the exit status non-zero")
    c.set_defaults(fn=cmd_check)
    sub.add_parser("list", help="list corpus cases").set_defaults(fn=cmd_list)
    c = sub.add_parser("show", help="describe one case and its expected outcome")
    c.add_argument("case")
    c.set_defaults(fn=cmd_show)
    c = sub.add_parser("generate", help="write the corpus (pcaps + manifest.json + SHA256SUMS)")
    c.add_argument("outdir")
    c.add_argument("--ipv6", action="store_true")
    c.add_argument("--vlan", type=int, action="append", help="add an 802.1Q tag (repeatable)")
    c.add_argument("--raw", action="store_true", help="LINKTYPE_RAW (no Ethernet header)")
    c.add_argument("--nano", action="store_true", help="nanosecond-resolution pcap")
    c.set_defaults(fn=cmd_generate)
    c = sub.add_parser("verify-corpus", help="regenerate and compare with a corpus directory")
    c.add_argument("dir", nargs="?", default="corpus")
    c.set_defaults(fn=cmd_verify_corpus)
    c = sub.add_parser("normalize", help="rewrite a capture so overlapping segments agree")
    c.add_argument("src")
    c.add_argument("dst")
    c.add_argument("--policy", default="first", choices=["first", "last", "lowseq"])
    c.add_argument("--no-checksum", action="store_true")
    c.set_defaults(fn=cmd_normalize)
    c = sub.add_parser("kernel-verify", help="replay the corpus into the live Linux TCP stack (root, /dev/net/tun)")
    c.add_argument("--out", help="write observations as JSON")
    c.add_argument("--permutations", action="store_true", help="also replay every arrival order of each case")
    c.add_argument("--fuzz", type=int, default=0, help="also replay N random scenarios")
    c.add_argument("--seed", type=int, default=1)
    c.set_defaults(fn=cmd_kernel)
    c = sub.add_parser("taps", help="score the built-in reference and flawed taps on the corpus")
    c.add_argument("--dir", default="corpus")
    c.add_argument("--kernel", help="kernel_observed.json for the fidelity column")
    c.set_defaults(fn=cmd_taps)
    c = sub.add_parser("tap-reader", help="run the corpus through the tap_reader Rust crate (needs cargo)")
    c.add_argument("--adapter-dir", default="adapters/tap_reader")
    c.add_argument("--dir", default="corpus")
    c.add_argument("--kernel", default="corpus/kernel_observed.json")
    c.add_argument("--mode", choices=["asis", "trim", "both"], default="both")
    c.add_argument("--out")
    c.add_argument("-v", "--verbose", action="store_true")
    c.set_defaults(fn=cmd_tap_reader)
    c = sub.add_parser("score", help="score another tap's JSON output: {case: {stream_hex, flagged}}")
    c.add_argument("results")
    c.add_argument("--dir", default="corpus")
    c.add_argument("--kernel")
    c.set_defaults(fn=cmd_score)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except BrokenPipeError:               # e.g. `packet-forge check ... | head`
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(main())
