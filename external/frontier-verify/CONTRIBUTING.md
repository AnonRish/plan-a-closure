# Contributing

## Before you write code

Read `docs/threat-model.md` and `docs/ai2040-coverage-matrix.md` first.
This project's value is entirely in the gap between what it claims and
what it actually does being zero. A pull request that makes a component
look more finished without making it more finished -- a docstring claiming
something the code doesn't do, a test that asserts a tautology, a status
label upgraded without new evidence backing it -- will be closed, no matter
how clean the code is otherwise.

## Maturity labels are load-bearing, not decorative

Use `frontier_verify.evidence.models.Maturity`'s vocabulary
(`NOT_IMPLEMENTED`, `MOCK`, `SIMULATED`, `EXPERIMENTAL`, `RESEARCH`,
`VALIDATED`, `PRODUCTION_READY`) exactly, and only move something to a
higher label when you can point to the specific new test, review, or
external validation that earned it. `VALIDATED` and `PRODUCTION_READY`
should be rare for a long time.

## Adding a new `AttestationProvider`

See `docs/hardware-provider-guide.md`. The short version: implement
`get_platform_evidence()`, set `mock=False` only if the evidence is real,
and don't claim a `maturity` your testing doesn't support.

## Tests

- `tests/unit/` -- one behavior per test, no network, no filesystem beyond
  what pytest's tmp fixtures give you.
- `tests/security/` -- attack something. If a security test can't fail
  when the code is broken, it isn't testing anything.
- `tests/adversarial/` -- same spirit, aimed at the policy/evaluation layer
  rather than the crypto layer.
- `tests/integration/` -- exercise the real FastAPI app via `TestClient`,
  end to end.

Run all of them with `pytest`, lint with `ruff check .` (see
`pyproject.toml` for the two deliberately-scoped exceptions and why they
exist).

## Divergences from the source specification

If you're changing something the original AI-2040-aligned specification
asked for, write an ADR in `docs/adr/` using the same structure as
`0001-attestation-abstraction-and-network-tap-deferral.md`: objective,
original mechanism, limitation, alternative, why it's stronger, what's
preserved, new assumptions, what's lost, remaining risks. Silently
diverging is worse than diverging with a documented reason.
