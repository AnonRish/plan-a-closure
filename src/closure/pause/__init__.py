"""closure.pause: the hardwired-pause layer.

Executable versions of the quantitative parts of "The Feasibility of a Hardwired Pause of Frontier AI Training"
(Working Group on AI Pause Feasibility, working paper v1.0.1, 10 October 2026), wired into the closure kit's evidence
format. The paper's own calculations supplement (MIT) and economics repository (MIT) are the reference for the
numbers; nothing from them is vendored here. See docs/HARDWIRED_PAUSE.md.

Every function states which section of the paper it implements. Nothing here is a claim about real stocks, real chips
or real treaty parties: inputs are the paper's illustrative values unless the caller supplies others."""
__all__ = ["units", "thresholds", "treaty_ledger", "census", "inference_only", "gemm_audit", "fab", "whitelist",
           "registry", "supply_chain", "transition", "msic_econ", "pausegame", "bridge", "paper_claims", "coverage"]
