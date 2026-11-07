# vLLM Integration

## Phase 3 review

Re-checked this phase per section 13's instruction to confirm
compatibility with current vLLM architecture rather than assume Phase 2's
research still holds. No new search this phase turned up anything
suggesting `vllm.stat_logger_plugins` or `StatLoggerBase` have changed or
been deprecated since Phase 2 -- nothing in this phase's (extensive)
research touched vLLM directly, so this is a confirmation that nothing
contradicted the prior finding, not a fresh independent re-verification.
**The exact method signatures on `StatLoggerBase` remain unconfirmed
against a live install**, same honest gap as Phase 2 -- this project still
has no vLLM installation to check against (heavy CUDA-oriented
dependency, no GPU in this environment). If picking this up next: install
vLLM in a real environment before writing the adapter body, not after.

Researched August 2026, against vLLM's current plugin architecture --
not assumed from older API knowledge, per the brief's section 9
instruction.

## The least invasive integration point found

vLLM has a formal plugin system built on Python `entry_points`, with
distinct plugin groups including `vllm.stat_logger_plugins` --
specifically for registering custom, out-of-tree loggers by subclassing
`StatLoggerBase`, without modifying vLLM's core or the model-serving hot
path. This is a materially better fit than a generic "wrap the inference
call" approach: it's an extension point vLLM already documents and
supports, observing request/response metadata that naturally includes
model identity and timing information, exactly the shape
`ModelIdentity`/`RuntimeIdentity` need.

Other plugin groups exist (`vllm.endpoint_plugins` for custom HTTP routes,
`vllm.general_plugins`, `vllm.platform_plugins`) but are either more
invasive (endpoint plugins run inside the trust boundary of the serving
process's HTTP surface) or not a fit for observability-only integration.

## Design

```python
# NOT tested against a live vLLM instance -- see "What's tested" below.
# Illustrative of the intended shape, targeting vllm.stat_logger_plugins'
# real, documented extension point.

from vllm.v1.metrics.loggers import StatLoggerBase  # verify this exact
                                                       # import path against
                                                       # your installed
                                                       # vLLM version before
                                                       # relying on it

from frontier_verify import VerifierClient
from frontier_verify.evidence.models import Evidence, ModelIdentity, RuntimeIdentity


class FrontierVerifyStatLogger(StatLoggerBase):
    """Registered via the vllm.stat_logger_plugins entry point. Submits
    evidence ASYNCHRONOUSLY (a background queue, not shown here) so a
    slow or unreachable verifier never blocks inference -- see "Overhead
    and failure isolation" below."""

    def __init__(self, vllm_config, engine_index: int = 0):
        self.client = VerifierClient(endpoint="https://verifier.example.com")
        self.model_identity = ModelIdentity(
            model_digest=vllm_config.model_config.model,  # placeholder --
            # the REAL digest needs to come from hashing actual weights,
            # not the model name string; this needs real design work, not
            # assumed correct here
        )

    def log(self, scheduler_stats, iteration_stats) -> None:
        # Real implementation: build an Evidence bundle from whatever
        # scheduler_stats/iteration_stats actually expose in the vLLM
        # version being targeted, then submit asynchronously. Exact
        # available fields need to be checked against a live install --
        # not done here, since none is available in this environment.
        ...
```

## Modes

`audit-only` (log evidence, never affects serving) is the only mode this
design should start in. `shadow` (evidence submitted, verification result
observed but not enforced) and `sampled` (only a fraction of requests
generate evidence) are natural next steps once `audit-only` is proven
reliable in a real deployment. **Enforcement is explicitly out of scope**
until the underlying verification actually justifies blocking real
inference traffic on it -- which, given `docs/assurance-model.md` caps
current assurance at L1, it does not yet.

## Overhead and failure isolation

Evidence submission MUST be asynchronous relative to the inference request
path -- a stat logger callback that blocks on a network call to the
verifier would turn every inference request's latency into a function of
verifier availability, which is unacceptable regardless of how good the
verification logic is. This needs a background queue/thread design that
this document specifies as a requirement, not as implemented code.

## What's tested vs. not

**Tested**: nothing against a live vLLM instance -- this environment has
no GPU and did not install vLLM (a multi-gigabyte dependency built around
CUDA). **Grounded in real, current research**: yes -- the
`stat_logger_plugins` mechanism and its purpose are confirmed from current
vLLM documentation, not assumed from memory. **Honest gap**: exact method
signatures on `StatLoggerBase` (what `log()` receives, exactly) need
verification against whichever vLLM version a real integration targets,
which the brief's own section 10 language ("clearly label what is
untested") requires stating plainly rather than guessing confidently.

## Next step if picked up

Install vLLM in an environment with real GPU access, subclass
`StatLoggerBase` against the actual current interface, and replace the
placeholder `model_digest` line above with real weights-hashing logic
before claiming this integration works.
