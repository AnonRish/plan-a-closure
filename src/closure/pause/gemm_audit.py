"""GEMM-laundering screen for inference-only accelerator designs (paper section 4.2).

An inference-only chip still performs dynamic matrix multiplications: attention's QK^T and AV have two runtime operands.
If an operator can write both operands and read the product, that unit is a general matrix multiplier, and general matrix
multiplication is what training needs. The paper's licensing criterion: for every dynamic matmul at least one operand must
come straight from a previous operation, or the output must go straight to the next one, with no exposure to the software
layer or to a physical interface (inter-chip links, off-chip memory, test and debug ports).

This module checks that criterion on a dataflow graph and reports how much of the chip's arithmetic is exposed, through
how many nonlinear stages, or sealed. It is a design-time screen. The paper requires an audit of a realised system,
including physical tampering paths; no graph replaces that. Ports of the intended token interface are not counted here:
that channel is bounded separately by inference_only.token_oracle_gemm_rate."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

KINDS = {"port", "token_port", "buffer", "linear", "nonlinear", "matmul_static", "matmul_dynamic"}
# What the operator can do to a value passing through a node of this kind. Fixed-weight linear maps are treated as
# transparent (an operator can choose inputs to reach a wanted operand); nonlinear stages, and dynamic matmuls whose output
# is bilinear in their inputs, are obstacles. The paper says only that more chained stages make an attack more formidable.
_OBSTACLE = {"nonlinear", "matmul_dynamic"}


@dataclass
class Design:
    name: str
    nodes: dict = field(default_factory=dict)       # id -> {"kind", "flops", "writable", "readable", "protected", ...}
    edges: list = field(default_factory=list)       # (src, dst, operand) with operand in {"a", "b", None}

    def add(self, node_id: str, kind: str, flops: float = 0.0, writable: bool = False, readable: bool = False,
            protected: bool = False, note: str = "") -> "Design":
        if kind not in KINDS:
            raise ValueError(f"unknown node kind {kind!r}")
        self.nodes[node_id] = {"kind": kind, "flops": flops, "writable": writable, "readable": readable,
                               "protected": protected, "note": note}
        return self

    def connect(self, src: str, dst: str, operand: str = None) -> "Design":
        self.edges.append((src, dst, operand))
        return self

    def protect(self, *port_ids: str) -> "Design":
        """Authenticate and encrypt a port with keys that live on the chip (the paper's suggested way to close a link)."""
        for p in port_ids:
            self.nodes[p]["protected"] = True
        return self


def design_from_dict(spec: dict) -> Design:
    """Build a Design from plain data so a chip team can audit its own dataflow graph from a JSON file:
    {"name": ..., "nodes": {id: {"kind": ..., "flops": ..., "writable": ..., "readable": ..., "protected": ...}},
     "edges": [[src, dst], [src, dst, "a"], ...]}"""
    d = Design(spec.get("name", "design"))
    for node_id, n in spec["nodes"].items():
        d.add(node_id, n["kind"], flops=n.get("flops", 0.0), writable=n.get("writable", False),
              readable=n.get("readable", False), protected=n.get("protected", False), note=n.get("note", ""))
    for e in spec["edges"]:
        d.connect(e[0], e[1], e[2] if len(e) > 2 else None)
    missing = [x for e in d.edges for x in e[:2] if x not in d.nodes]
    if missing:
        raise ValueError(f"edges refer to unknown nodes: {sorted(set(missing))}")
    return d


def design_to_dict(d: Design) -> dict:
    return {"name": d.name, "nodes": {i: dict(n) for i, n in d.nodes.items()},
            "edges": [[s, t] if op is None else [s, t, op] for s, t, op in d.edges]}


def _is_source(n: dict) -> bool:
    return n["kind"] == "port" and n["writable"] and not n["protected"]


def _is_sink(n: dict) -> bool:
    return n["kind"] == "port" and n["readable"] and not n["protected"]


def _write_cost(d: Design) -> dict:
    """Fewest obstacle stages between an unprotected writable port and each node's output (inclusive of the node)."""
    cost = {i: (0 if _is_source(n) else math.inf) for i, n in d.nodes.items()}
    for _ in range(len(d.nodes) + 1):
        changed = False
        for s, t, _op in d.edges:
            c = cost[s] + (1 if d.nodes[t]["kind"] in _OBSTACLE else 0)
            if c < cost[t]:
                cost[t], changed = c, True
        if not changed:
            break
    return cost


def _read_cost(d: Design) -> dict:
    """Fewest obstacle stages between each node's output and an unprotected readable port (exclusive of the node)."""
    cost = {i: (0 if _is_sink(n) else math.inf) for i, n in d.nodes.items()}
    for _ in range(len(d.nodes) + 1):
        changed = False
        for s, t, _op in d.edges:
            c = cost[t] + (1 if d.nodes[t]["kind"] in _OBSTACLE else 0)
            if c < cost[s]:
                cost[s], changed = c, True
        if not changed:
            break
    return cost


@dataclass
class AuditResult:
    design: str
    matmuls: list
    total_flops: float
    exposed_flops: float
    obstructed_flops: float
    sealed_flops: float

    @property
    def exposed_fraction(self) -> float:
        """Share of the chip's inference arithmetic that is directly launderable. Zero meets the paper's criterion."""
        return self.exposed_flops / self.total_flops if self.total_flops else 0.0

    @property
    def exposed_or_obstructed_fraction(self) -> float:
        """Upper end of the range if the operator can defeat the nonlinear stages in between."""
        return (self.exposed_flops + self.obstructed_flops) / self.total_flops if self.total_flops else 0.0

    @property
    def passes_licensing_criterion(self) -> bool:
        return self.exposed_flops == 0.0

    def findings(self) -> list:
        out = []
        for m in self.matmuls:
            if m["class"] == "exposed":
                out.append(f"{m['id']}: both operands writable and output readable through unprotected ports; "
                           f"protect those ports or seal their endpoints in one package")
            elif m["class"] == "obstructed":
                out.append(f"{m['id']}: reachable through {m['depth']} nonlinear stage(s); relies on them as the only barrier")
        return out


def audit(d: Design) -> AuditResult:
    wc, rc = _write_cost(d), _read_cost(d)
    operands = {}
    for s, t, op in d.edges:
        if op in ("a", "b"):
            operands.setdefault(t, {}).setdefault(op, []).append(s)
    rows, exposed, obstructed, sealed, total = [], 0.0, 0.0, 0.0, 0.0
    for i, n in d.nodes.items():
        if n["kind"] in ("matmul_static", "matmul_dynamic"):
            total += n["flops"]
        if n["kind"] != "matmul_dynamic":
            continue
        ops = operands.get(i, {})
        d_a = min((wc[x] for x in ops.get("a", [])), default=math.inf)
        d_b = min((wc[x] for x in ops.get("b", [])), default=math.inf)
        d_out = rc[i]
        depth = max(d_a, d_b, d_out)
        klass = "exposed" if depth == 0 else ("sealed" if math.isinf(depth) else "obstructed")
        rows.append({"id": i, "flops": n["flops"], "d_a": d_a, "d_b": d_b, "d_out": d_out, "class": klass,
                     "depth": None if math.isinf(depth) else int(depth)})
        if klass == "exposed":
            exposed += n["flops"]
        elif klass == "obstructed":
            obstructed += n["flops"]
        else:
            sealed += n["flops"]
    return AuditResult(d.name, rows, total, exposed, obstructed, sealed)


def attention_flop_share(d_model: float, n_ctx: float) -> float:
    """Dynamic (attention-score and value) share of a transformer layer's arithmetic: n / (6 d + n) for an MLP ratio of 4.
    Small at short context, a majority at long context; it is the part an exposed design would hand to an operator."""
    return n_ctx / (6.0 * d_model + n_ctx)


def example_attention_block(open_links: bool = True, sealed_package: bool = False, authenticated_links: bool = False,
                            d_model: float = 4096, n_ctx: float = 8192) -> Design:
    """A toy dataflow built from the channels the paper describes for the HNLPU (section 4.3 and footnote 46), NOT the actual
    design: K and V arrive from a memory buffer on a bus, Q is a partial sum travelling over inter-chip links, and the
    score and value products are summed over the same links. `sealed_package` puts the four chips in one package (no
    external links); `authenticated_links` protects the links with on-chip keys. `open_links=False` is the same as sealing."""
    share = attention_flop_share(d_model, n_ctx)
    per_attn = 100.0 * share / 2.0                 # two dynamic matmuls, in arbitrary units out of 100 total
    d = Design("hnlpu-like attention block")
    d.add("token_in", "token_port")                # the intended interface: bounded by the token-oracle rate, not screened here
    d.add("embed", "linear")
    d.add("ln", "nonlinear")
    d.add("proj_q", "matmul_static", flops=100.0 * (1 - share) / 6)
    d.add("proj_k", "matmul_static", flops=100.0 * (1 - share) / 6)
    d.add("proj_v", "matmul_static", flops=100.0 * (1 - share) / 6)
    d.add("score", "matmul_dynamic", flops=per_attn)
    d.add("softmax", "nonlinear")
    d.add("value", "matmul_dynamic", flops=per_attn)
    d.add("mlp", "matmul_static", flops=100.0 * (1 - share) / 2)
    d.add("token_out", "token_port")
    for a, b in [("token_in", "embed"), ("embed", "ln"), ("ln", "proj_q"), ("ln", "proj_k"), ("ln", "proj_v")]:
        d.connect(a, b)
    d.connect("proj_q", "score", "a")
    d.connect("proj_k", "score", "b")
    d.connect("score", "softmax")
    d.connect("softmax", "value", "a")
    d.connect("proj_v", "value", "b")
    d.connect("value", "mlp")
    d.connect("mlp", "token_out")
    if open_links and not sealed_package:
        d.add("hbm_bus", "port", writable=True, readable=True, protected=authenticated_links)
        d.add("cxl_link", "port", writable=True, readable=True, protected=authenticated_links)
        d.add("k_buffer", "buffer")
        d.add("v_buffer", "buffer")
        d.add("q_buffer", "buffer")
        d.connect("hbm_bus", "k_buffer")
        d.connect("k_buffer", "score", "b")
        d.connect("hbm_bus", "v_buffer")
        d.connect("v_buffer", "value", "b")
        d.connect("cxl_link", "q_buffer")
        d.connect("q_buffer", "score", "a")
        d.connect("score", "cxl_link")             # partial sums of the score product
        d.connect("value", "cxl_link")             # partial sums of the value product
    return d
