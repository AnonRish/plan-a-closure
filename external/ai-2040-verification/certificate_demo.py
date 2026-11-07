"""
§13: not a real DSL-to-PTX compiler (out of scope for a one-line source and
a sandbox with no GPU) — a small, real demonstration of the actual load-
bearing mechanism underneath "machine-checkable certificate": deterministic
compilation. If compiling the same declared workload always produces the
same instruction bytes, a hash of those bytes IS a certificate anyone can
check without re-trusting the compiler each time (the standard reproducible-
builds argument, applied here instead of to software supply chains). This
uses gcc against a toy C stand-in for "GPU instructions" — real enough to
show the mechanism holds, honestly not a claim about real PTX toolchains.
"""
import hashlib
import subprocess
import json

DSL_APPROVED = """
workload inference_v1 {
    checkpoint_hash: a3f8e91c9e21
    operation_class: FORWARD_ONLY
    max_batch_size: 256
    allowed_ops: [matmul, attention, layernorm, gelu]
    collective_ops: NONE
}
"""

DSL_DIFFERENT = """
workload inference_v1 {
    checkpoint_hash: a3f8e91c9e21
    operation_class: FORWARD_ONLY
    max_batch_size: 512
    allowed_ops: [matmul, attention, layernorm, gelu]
    collective_ops: NONE
}
"""


def parse_dsl(source: str) -> dict:
    """Deliberately trivial parser — the point is determinism end to end,
    not language design."""
    fields = {}
    for line in source.strip().splitlines():
        line = line.strip().rstrip(",")
        if ":" in line and "{" not in line and "}" not in line and "workload" not in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


def compile_to_c(fields: dict) -> str:
    """Stand-in 'compiler': deterministically emit C source representing
    the declared workload's bounds as compiled constants — structurally
    playing the role a real DSL-to-PTX compiler would, emitting fixed
    instruction sequences from fixed declared bounds, not interpreting
    anything at runtime."""
    ops = fields.get("allowed_ops", "[]").strip("[]")
    op_list = ", ".join(f'"{o.strip()}"' for o in ops.split(","))
    return f"""
#include <stdio.h>
// AUTO-GENERATED — do not hand-edit. Compiled from an approved DSL workload
// declaration; this file's existence at all is what a raw-CUDA/PTX bypass
// skips entirely (see write-up).
static const char CHECKPOINT_HASH[] = "{fields.get('checkpoint_hash', '')}";
static const char OPERATION_CLASS[] = "{fields.get('operation_class', '')}";
static const int MAX_BATCH_SIZE = {fields.get('max_batch_size', '0')};
static const char* ALLOWED_OPS[] = {{{op_list}}};
static const char COLLECTIVE_OPS[] = "{fields.get('collective_ops', '')}";

int main(void) {{
    // Every declared field is actually READ here — not decorative. The
    // first version of this generator declared these as unused static
    // consts, and -O2 dead-code-eliminated all of them: two DIFFERENT
    // declared workloads (max_batch_size 256 vs 512) compiled to
    // BIT-IDENTICAL binaries, silently defeating the entire certificate
    // mechanism, because nothing in the compiled output actually depended
    // on the value being certified. Caught by test 2 below actually
    // failing, not assumed to be fine because the code "looked" like it
    // encoded the bound.
    printf("checkpoint=%s class=%s max_batch=%d collectives=%s\\n",
           CHECKPOINT_HASH, OPERATION_CLASS, MAX_BATCH_SIZE, COLLECTIVE_OPS);
    for (int i = 0; i < (sizeof(ALLOWED_OPS) / sizeof(ALLOWED_OPS[0])); i++) {{
        printf("op: %s\\n", ALLOWED_OPS[i]);
    }}
    return 0;
}}
"""


def compile_and_certify(dsl_source: str, out_name: str) -> dict:
    fields = parse_dsl(dsl_source)
    c_source = compile_to_c(fields)
    # Fixed, content-independent-of-out_name source filename — compiling
    # "run_a.c" and "run_b.c" with byte-identical CONTENT still produced
    # different hashes on the first attempt, because the filename itself
    # leaks into the compiled output (debug/symbol metadata). This is a
    # well-known real gotcha in the actual reproducible-builds world, not
    # a contrived one; the fix (compile everything under one fixed
    # filename, using -ffile-prefix-map to normalize the reported path
    # too) is the same fix real toolchains use.
    c_path = "workload_src.c"
    bin_path = f"{out_name}.bin"
    with open(c_path, "w") as f:
        f.write(c_source)

    subprocess.run(
        ["gcc", "-O2", "-frandom-seed=fixed", "-fno-ident",
         "-ffile-prefix-map=" + __import__("os").getcwd() + "=/build",
         "-Wl,--build-id=none", "-static",
         "-o", bin_path, c_path],
        check=True, capture_output=True,
    )

    with open(bin_path, "rb") as f:
        binary_bytes = f.read()
    cert_hash = hashlib.sha256(binary_bytes).hexdigest()

    return {
        "dsl_source_hash": hashlib.sha256(dsl_source.encode()).hexdigest()[:16],
        "compiled_binary_hash": cert_hash,
        "binary_size": len(binary_bytes),
    }


if __name__ == "__main__":
    print("=" * 90)
    print("1. Same approved DSL source, compiled twice independently — must match exactly")
    print("=" * 90)
    cert_a = compile_and_certify(DSL_APPROVED, "run_a")
    cert_b = compile_and_certify(DSL_APPROVED, "run_b")
    print(json.dumps(cert_a, indent=2))
    print(json.dumps(cert_b, indent=2))
    print(f"Certificates match: {cert_a['compiled_binary_hash'] == cert_b['compiled_binary_hash']}")

    print()
    print("=" * 90)
    print("2. A DIFFERENT declared workload (max_batch_size 256 -> 512) — must NOT match")
    print("=" * 90)
    cert_c = compile_and_certify(DSL_DIFFERENT, "run_c")
    print(f"cert_a hash: {cert_a['compiled_binary_hash'][:24]}...")
    print(f"cert_c hash: {cert_c['compiled_binary_hash'][:24]}...")
    print(f"Certificates match: {cert_a['compiled_binary_hash'] == cert_c['compiled_binary_hash']} (must be False)")

    print()
    print("=" * 90)
    print("3. Tampering with the compiled binary AFTER certification — must be caught")
    print("=" * 90)
    with open("run_a.bin", "rb") as f:
        tampered = bytearray(f.read())
    tampered[-1] ^= 0xFF  # flip one bit near the end, simulating a
                            # post-compilation swap to different instructions
    tampered_hash = hashlib.sha256(bytes(tampered)).hexdigest()
    print(f"original certified hash: {cert_a['compiled_binary_hash'][:24]}...")
    print(f"tampered binary hash:    {tampered_hash[:24]}...")
    print(f"Tamper detected: {tampered_hash != cert_a['compiled_binary_hash']}")

    print()
    print("=" * 90)
    print("4. THE GAP: raw instructions written directly, bypassing the DSL/compiler entirely")
    print("=" * 90)
    # Someone writes semantically-equivalent C directly, achieving the exact
    # same runtime behavior, without ever going through parse_dsl/compile_to_c.
    raw_source = """
#include <stdio.h>
int main(void) {
    printf("checkpoint=a3f8e91c9e21 class=FORWARD_ONLY max_batch=256 collectives=NONE\\n");
    printf("op: matmul\\n"); printf("op: attention\\n"); printf("op: layernorm\\n"); printf("op: gelu\\n");
    return 0;
}
"""
    with open("raw_bypass.c", "w") as f:
        f.write(raw_source)
    subprocess.run(["gcc", "-O2", "-frandom-seed=fixed", "-fno-ident",
                     "-ffile-prefix-map=" + __import__("os").getcwd() + "=/build",
                     "-Wl,--build-id=none", "-static",
                     "-o", "raw_bypass.bin", "raw_bypass.c"], check=True, capture_output=True)
    with open("raw_bypass.bin", "rb") as f:
        raw_hash = hashlib.sha256(f.read()).hexdigest()
    print(f"raw bypass binary hash: {raw_hash[:24]}...")
    print("There is no DSL source this hash traces back to, no certificate was ever issued for")
    print("it, and no approved-workload registry entry exists to compare it against. The")
    print("mechanism above has *nothing to say* about this binary — not 'flagged', not 'unknown",
          "risk', literally outside its scope. That's the gap, demonstrated rather than asserted:")
    print("this only works if reaching the GPU without going through the DSL compiler is itself")
    print("prohibited by policy — a §23/§29 question, not something recompilable-certificate")
    print("technology can close from this side.")
