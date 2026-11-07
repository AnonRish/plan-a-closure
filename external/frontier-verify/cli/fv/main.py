"""The `fv` CLI. Phase 1 covers: version, init, doctor, attest, evidence
build/verify, receipt verify, policy validate.

`fv doctor` is the one command the source spec calls out by name: "Never
print PASS without performing the underlying check." Every check function
below does something real (import, subprocess, filesystem stat) rather than
returning a hardcoded True.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import typer

from frontier_verify.attestations.mock_provider import MockAttestationProvider
from frontier_verify.evidence.models import Evidence, HardwareEvidence, ModelIdentity, RuntimeIdentity
from frontier_verify.policies.models import Policy
from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import (
    generate_keypair,
    private_key_to_hex,
    public_key_from_hex,
    public_key_to_hex,
    verify_receipt,
)

app = typer.Typer(help="Frontier Verify CLI (Phase 1 -- local/offline core)", no_args_is_help=True)
evidence_app = typer.Typer(help="Build and verify evidence bundles")
receipt_app = typer.Typer(help="Inspect and verify signed receipts")
policy_app = typer.Typer(help="Validate policy documents")
app.add_typer(evidence_app, name="evidence")
app.add_typer(receipt_app, name="receipt")
app.add_typer(policy_app, name="policy")

CONFIG_DIR = Path.home() / ".frontier-verify"


@app.command()
def version() -> None:
    "Print the Frontier Verify version."
    typer.echo("frontier-verify 0.4.0 (Phase 4)")


@app.command()
def init() -> None:
    "Generate a local demo Ed25519 keypair and a starter policy. Not a KMS."
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    sk, pk = generate_keypair()
    (CONFIG_DIR / "verifier_private_key.hex").write_text(private_key_to_hex(sk))
    (CONFIG_DIR / "verifier_public_key.hex").write_text(public_key_to_hex(pk))
    policy = Policy(
        policy_id="frontier-inference-baseline",
        version="0.1.0",
        allow_mock_hardware=True,
        description=(
            "Phase 1 demo policy. allow_mock_hardware=True so the local "
            "demo can pass without real GPU hardware. A real deployment "
            "policy must set this to False."
        ),
    )
    (CONFIG_DIR / "policy.json").write_text(policy.model_dump_json(indent=2))
    typer.echo(f"Initialized {CONFIG_DIR}")
    typer.echo(
        "Generated a LOCAL DEMO keypair -- not a production key management "
        "setup. See docs/receipt-specification.md."
    )


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "NOT AVAILABLE"
    line = f"[{status:14}] {label}"
    if detail:
        line += f" -- {detail}"
    typer.echo(line)
    return ok


@app.command()
def doctor() -> None:
    "Run real environment checks. Never prints PASS without checking."
    typer.echo("Frontier Verify doctor\n")

    _check("python >= 3.10", sys.version_info >= (3, 10), sys.version.split()[0])

    try:
        import cryptography

        _check("cryptography library", True, cryptography.__version__)
    except ImportError:
        _check("cryptography library", False, "pip install cryptography")

    try:
        import fastapi

        _check("fastapi library", True, fastapi.__version__)
    except ImportError:
        _check("fastapi library", False, "pip install fastapi")

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            out = subprocess.run(
                [nvidia_smi, "-L"], capture_output=True, text=True, timeout=5, check=False
            )
            _check("NVIDIA GPU (nvidia-smi)", out.returncode == 0, out.stdout.strip() or out.stderr.strip())
        except Exception as e:  # noqa: BLE001 -- deliberate: `doctor` must report every
            # failure mode of an external binary (missing, hung, permission denied, ...)
            # as NOT AVAILABLE rather than crashing the whole command.
            _check("NVIDIA GPU (nvidia-smi)", False, str(e))
    else:
        _check(
            "NVIDIA GPU (nvidia-smi)",
            False,
            "nvidia-smi not on PATH -- real hardware attestation (Phase 2) unavailable here",
        )

    _check("docker", shutil.which("docker") is not None, "not required for the Phase 1 local demo")

    config_exists = CONFIG_DIR.exists()
    _check("local config (`fv init`)", config_exists, str(CONFIG_DIR) if config_exists else "run `fv init` first")

    typer.echo(
        "\nReal NVIDIA/NVSwitch attestation is still NOT implemented "
        "regardless of what the checks above found -- see "
        "docs/hardware/nvat-integration.md for current status."
    )


@app.command()
def attest(out: Path = typer.Option(Path("attestation.json"), help="output file")) -> None:
    "Produce a MOCK hardware attestation (no real GPU integration in Phase 1)."
    hw = MockAttestationProvider().get_platform_evidence()
    out.write_text(hw.model_dump_json(indent=2))
    typer.echo(f"Wrote MOCK hardware evidence to {out}")
    typer.echo("This proves nothing about real hardware. See docs/ai2040-coverage-matrix.md.")


@evidence_app.command("build")
def evidence_build(
    model_digest: str = typer.Option(..., help="digest identifying the model/weights"),
    attestation_file: Path = typer.Option(..., help="output of `fv attest`"),
    serving_engine: str = typer.Option("local-cli-demo"),
    out: Path = typer.Option(Path("evidence.json")),
) -> None:
    "Build an Evidence bundle from a model digest + attestation file."
    hw = HardwareEvidence.model_validate(json.loads(attestation_file.read_text()))
    ev = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest=model_digest),
        runtime_identity=RuntimeIdentity(serving_engine=serving_engine),
        hardware_evidence=hw,
    )
    out.write_text(ev.model_dump_json(indent=2))
    typer.echo(f"Wrote evidence bundle to {out} (digest={ev.digest()})")


@evidence_app.command("verify")
def evidence_verify(evidence_file: Path) -> None:
    "Check an evidence bundle's internal structural validity."
    ev = Evidence.model_validate(json.loads(evidence_file.read_text()))
    typer.echo(f"structurally valid. digest={ev.digest()}")


@receipt_app.command("verify")
def receipt_verify(
    receipt_file: Path,
    public_key_hex: str | None = typer.Option(
        None, help="verifier public key hex; defaults to the local demo key from `fv init`"
    ),
) -> None:
    "Independently verify a receipt's signature -- fully offline, no network call."
    receipt = Receipt.model_validate(json.loads(receipt_file.read_text()))
    if public_key_hex is None:
        pk_path = CONFIG_DIR / "verifier_public_key.hex"
        if not pk_path.exists():
            typer.echo("No public key provided and none found from `fv init`.")
            raise typer.Exit(1)
        public_key_hex = pk_path.read_text().strip()
    ok = verify_receipt(receipt, public_key_from_hex(public_key_hex))
    typer.echo(f"signature_valid={ok}")
    if not ok:
        raise typer.Exit(1)


@policy_app.command("validate")
def policy_validate(policy_file: Path) -> None:
    "Validate a policy document's structure."
    p = Policy.model_validate(json.loads(policy_file.read_text()))
    typer.echo(f"policy {p.policy_id} v{p.version} is structurally valid")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
