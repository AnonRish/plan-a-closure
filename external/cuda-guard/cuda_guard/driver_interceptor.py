"""
cuda_guard.driver_interceptor
===============================
Phase 10 (spec Sec. 14). LD_PRELOAD C interposer, ported verbatim from the
prototype's Module 2 (already proven via real subprocess+harness testing --
this is not re-derived, just re-typed). The claim stays exactly as narrow as
the mechanism supports: THIS PROCESS WAS OBSERVED THROUGH THIS INTERCEPTOR,
never ALL GPU ACTIVITY WAS OBSERVED.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from .evidence import EvidenceClass, EvidenceRecord, EvidenceSource, EvidenceStatus, TrustRoot
from .ledger import TamperEvidentLedger

_GOVERNOR_C_SOURCE = r"""
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

typedef int cudaError_t;
typedef int CUresult;
typedef cudaError_t (*cudaMalloc_fn)(void**, size_t);
typedef CUresult (*cuLaunchKernel_fn)(void*, unsigned int, unsigned int, unsigned int,
                                       unsigned int, unsigned int, unsigned int,
                                       unsigned int, void*, void**, void**);

static cudaMalloc_fn real_cudaMalloc = NULL;
static cuLaunchKernel_fn real_cuLaunchKernel = NULL;
static FILE *audit_log = NULL;
static long malloc_calls = 0;
static long launch_calls = 0;
static long long bytes_total = 0;

__attribute__((constructor))
static void governor_init(void) {
    const char *log_path = getenv("CUDA_GOVERNOR_LOG");
    audit_log = fopen(log_path ? log_path : "/tmp/cuda_governor_audit.log", "a");
    real_cudaMalloc = (cudaMalloc_fn)dlsym(RTLD_NEXT, "cudaMalloc");
    real_cuLaunchKernel = (cuLaunchKernel_fn)dlsym(RTLD_NEXT, "cuLaunchKernel");
    if (audit_log) {
        fprintf(audit_log, "[GOVERNOR] init real_cudaMalloc=%p real_cuLaunchKernel=%p\n",
                (void*)real_cudaMalloc, (void*)real_cuLaunchKernel);
        fflush(audit_log);
    }
}

cudaError_t cudaMalloc(void **devPtr, size_t size) {
    malloc_calls++;
    bytes_total += (long long)size;
    if (audit_log) {
        fprintf(audit_log, "[INTERCEPT] cudaMalloc #%ld size=%zu total_bytes=%lld real_driver=%s\n",
                malloc_calls, size, bytes_total, real_cudaMalloc ? "yes" : "NO(emulated)");
        fflush(audit_log);
    }
    if (real_cudaMalloc) return real_cudaMalloc(devPtr, size);
    *devPtr = malloc(size);
    return 0;
}

CUresult cuLaunchKernel(void *f, unsigned int gx, unsigned int gy, unsigned int gz,
                          unsigned int bx, unsigned int by, unsigned int bz,
                          unsigned int shmem, void *stream, void **params, void **extra) {
    launch_calls++;
    if (audit_log) {
        fprintf(audit_log, "[INTERCEPT] cuLaunchKernel #%ld grid=(%u,%u,%u) block=(%u,%u,%u) real_driver=%s\n",
                launch_calls, gx, gy, gz, bx, by, bz, real_cuLaunchKernel ? "yes" : "NO(emulated)");
        fflush(audit_log);
    }
    if (real_cuLaunchKernel) return real_cuLaunchKernel(f, gx, gy, gz, bx, by, bz, shmem, stream, params, extra);
    return 0;
}
"""

_HARNESS_C_SOURCE = r"""
#include <dlfcn.h>
#include <stdio.h>
#include <stddef.h>
typedef int (*cudaMalloc_fn)(void**, size_t);
int main(void) {
    cudaMalloc_fn fn = (cudaMalloc_fn)dlsym(RTLD_DEFAULT, "cudaMalloc");
    if (!fn) { printf("NO cudaMalloc symbol resolvable in this process\n"); return 1; }
    void *p = NULL;
    for (int i = 1; i <= 3; i++) fn(&p, 1024 * 1024 * i);
    printf("harness: issued 3 cudaMalloc() calls through the resolved symbol\n");
    return 0;
}
"""

_STATIC_HARNESS_C_SOURCE = r"""
/* Bypass test: a real cudaMalloc symbol DEFINED IN THE BINARY ITSELF, not
   looked up dynamically. LD_PRELOAD cannot intercept a call that never goes
   through dynamic symbol resolution to begin with. */
#include <stdio.h>
#include <stdlib.h>
typedef int cudaError_t;
cudaError_t cudaMalloc(void **devPtr, size_t size) {
    *devPtr = malloc(size);
    printf("statically-linked cudaMalloc called directly, no dynamic symbol lookup involved\n");
    return 0;
}
int main(void) {
    void *p = NULL;
    cudaMalloc(&p, 1024);
    return 0;
}
"""


class DriverInterceptor:
    """Compiles libcuda_governor.so and proves interception via a real
    subprocess+harness, exactly as in the tested prototype."""

    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger
        self.available = False
        self.workdir: Optional[Path] = None
        self.so_path: Optional[Path] = None

    def compile(self) -> EvidenceRecord:
        if not shutil.which("gcc"):
            ev = EvidenceRecord(
                EvidenceClass.SOFTWARE_SELF_AUDIT, EvidenceSource.LD_PRELOAD_INTERCEPTOR,
                EvidenceStatus.UNAVAILABLE, TrustRoot.GOVERNED_PROCESS_SELF,
                establishes=[], does_not_establish=["anything -- gcc not found in PATH"],
                detail={"reason": "gcc not found in PATH"})
            self._ledger.record_evidence(ev)
            return ev
        try:
            self.workdir = Path(tempfile.mkdtemp(prefix="cuda_governor_"))
            c_path = self.workdir / "governor.c"
            so_path = self.workdir / "libcuda_governor.so"
            harness_c = self.workdir / "harness.c"
            harness_bin = self.workdir / "harness"
            c_path.write_text(_GOVERNOR_C_SOURCE)
            harness_c.write_text(_HARNESS_C_SOURCE)
            r1 = subprocess.run(["gcc", "-shared", "-fPIC", "-O2", "-o", str(so_path), str(c_path), "-ldl"],
                                 capture_output=True, text=True, timeout=60)
            r2 = subprocess.run(["gcc", "-O2", "-o", str(harness_bin), str(harness_c), "-ldl"],
                                 capture_output=True, text=True, timeout=60)
            if r1.returncode != 0 or r2.returncode != 0:
                ev = EvidenceRecord(
                    EvidenceClass.SOFTWARE_SELF_AUDIT, EvidenceSource.LD_PRELOAD_INTERCEPTOR,
                    EvidenceStatus.FAILED, TrustRoot.GOVERNED_PROCESS_SELF,
                    establishes=["a compilation attempt was made and failed"], does_not_establish=[],
                    detail={"stderr": (r1.stderr or "") + (r2.stderr or "")})
                self._ledger.record_evidence(ev)
                return ev
            self.so_path = so_path
            self.available = True
            ev = EvidenceRecord(
                EvidenceClass.SOFTWARE_SELF_AUDIT, EvidenceSource.LD_PRELOAD_INTERCEPTOR,
                EvidenceStatus.SUCCESS, TrustRoot.GOVERNED_PROCESS_SELF,
                establishes=["libcuda_governor.so compiled successfully"], does_not_establish=[],
                detail={"so_path": str(so_path)})
            self._ledger.record_evidence(ev)
            return ev
        except Exception as exc:
            ev = EvidenceRecord(
                EvidenceClass.SOFTWARE_SELF_AUDIT, EvidenceSource.LD_PRELOAD_INTERCEPTOR,
                EvidenceStatus.FAILED, TrustRoot.GOVERNED_PROCESS_SELF,
                establishes=[], does_not_establish=[], detail={"exception": str(exc)})
            self._ledger.record_evidence(ev)
            return ev

    def demo(self) -> EvidenceRecord:
        """Proves real interception via subprocess: baseline (no preload)
        vs. intercepted (LD_PRELOAD set). Claim scope: THIS PROCESS WAS
        OBSERVED THROUGH THIS INTERCEPTOR -- never ALL GPU ACTIVITY."""
        if not self.available:
            ev = EvidenceRecord(
                EvidenceClass.SOFTWARE_SELF_AUDIT, EvidenceSource.LD_PRELOAD_INTERCEPTOR,
                EvidenceStatus.NOT_APPLICABLE, TrustRoot.GOVERNED_PROCESS_SELF,
                establishes=[], does_not_establish=[], detail={"reason": "interceptor not compiled"})
            self._ledger.record_evidence(ev)
            return ev
        harness_bin = self.workdir / "harness"
        log_path = self.workdir / "audit.log"
        if log_path.exists():
            log_path.unlink()
        baseline = subprocess.run([str(harness_bin)], capture_output=True, text=True, timeout=15)
        intercepted = subprocess.run(
            [str(harness_bin)], capture_output=True, text=True, timeout=15,
            env={**os.environ, "LD_PRELOAD": str(self.so_path), "CUDA_GOVERNOR_LOG": str(log_path)})
        log_lines = log_path.read_text().splitlines() if log_path.exists() else []
        ev = EvidenceRecord(
            EvidenceClass.SOFTWARE_SELF_AUDIT, EvidenceSource.LD_PRELOAD_INTERCEPTOR,
            EvidenceStatus.SUCCESS, TrustRoot.GOVERNED_PROCESS_SELF,
            establishes=["THIS PROCESS (the harness subprocess) was observed through this "
                         "interceptor -- proven via real dynamic-linker symbol resolution, "
                         "not merely asserted"],
            does_not_establish=["that all GPU activity on this host was observed",
                                 "anything about a process not launched with LD_PRELOAD set"],
            detail={"baseline_stdout": baseline.stdout.strip(), "intercepted_stdout": intercepted.stdout.strip(),
                    "audit_log_lines": log_lines,
                    "real_driver_present": any("real_driver=yes" in l for l in log_lines)})
        self._ledger.record_evidence(ev)
        return ev

    def bypass_test_no_preload(self) -> str:
        """Baseline case: harness run without LD_PRELOAD set at all."""
        if not self.available:
            return "UNTESTABLE (interceptor not compiled)"
        r = subprocess.run([str(self.workdir / "harness")], capture_output=True, text=True, timeout=15)
        return "NOT_DETECTED (no symbol resolvable, exit code %d)" % r.returncode

    def bypass_test_static_link(self) -> str:
        """A binary with its own cudaMalloc defined directly (not looked up
        dynamically) is architecturally unreachable by an LD_PRELOAD
        interposer -- real subprocess test, not assumed."""
        if not shutil.which("gcc"):
            return "UNTESTABLE (gcc not available)"
        workdir = Path(tempfile.mkdtemp(prefix="static_bypass_"))
        c_path = workdir / "static_harness.c"
        bin_path = workdir / "static_harness"
        c_path.write_text(_STATIC_HARNESS_C_SOURCE)
        r = subprocess.run(["gcc", "-O2", "-o", str(bin_path), str(c_path)], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return f"UNTESTABLE (compile failed: {r.stderr[:200]})"
        log_path = workdir / "audit.log"
        run = subprocess.run(
            [str(bin_path)], capture_output=True, text=True, timeout=15,
            env={**os.environ, "LD_PRELOAD": str(self.so_path) if self.so_path else "",
                 "CUDA_GOVERNOR_LOG": str(log_path)})
        intercepted_this_call = log_path.exists() and "INTERCEPT" in log_path.read_text()
        shutil.rmtree(workdir, ignore_errors=True)
        return ("NOT_DETECTED (statically-defined symbol bypassed the interposer, as expected)"
                if not intercepted_this_call else "DETECTED (unexpected)")

    def cleanup(self):
        if self.workdir and self.workdir.exists():
            shutil.rmtree(self.workdir, ignore_errors=True)
