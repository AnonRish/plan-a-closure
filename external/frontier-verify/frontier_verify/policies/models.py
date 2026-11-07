"""Policy documents.

A real policy library (frontier-inference-baseline, high-assurance,
regulated-deployment, research-only, ...) is future work -- see
docs/protocol-roadmap.md. Phase 1 ships one honest, minimal Policy schema
and one evaluator so that "what does this policy actually check" has a
single, readable answer instead of eight templates nobody has audited.
"""
from __future__ import annotations

from pydantic import BaseModel


class Policy(BaseModel):
    policy_id: str
    version: str
    allow_mock_hardware: bool = False
    max_evidence_age_seconds: int = 3600
    description: str = ""
