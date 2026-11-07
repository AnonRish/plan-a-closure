"""
FastAPI backend implementing §5. Two independently-loaded model instances
(prover's copy, verifier's copy) stand in for "separate prover and verifier
vLLM instances" — same checkpoint file, loaded twice, exactly as an honest
deployment would have matching weights on both sides while remaining
architecturally separate processes/objects.

Seed custody, the actual security-relevant design point: /verify's request
model has NO seed field. The seed used for verification is *always* read
from the sessions row the verifier itself created in /session/start — never
from anything the caller of /verify sends. A prover cannot change what seed
gets checked against by any means this API exposes, because there's no
parameter that would let them try.
"""
import secrets
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

from model import TinyCharLM
import sampling
import difr
import db

app = FastAPI(title="DiFR Recomputation Server (§5 prototype)")

# Two independently loaded instances of the same checkpoint — "separate
# prover and verifier model instances" as the task specifies.
prover_model = TinyCharLM.load("charlm.pkl")
verifier_model = TinyCharLM.load("charlm.pkl")

import pickle
with open("vocab.pkl", "rb") as f:
    _vocab = pickle.load(f)
STOI, ITOS = _vocab["stoi"], _vocab["itos"]

TAU = None  # set by §11's calibration; loaded from file if present


def encode(s: str) -> list[int]:
    return [STOI[c] for c in s]


def decode(tokens: list[int]) -> str:
    return "".join(ITOS[t] for t in tokens)


@app.on_event("startup")
def startup():
    db.init_schema()
    global TAU
    try:
        with open("tau.txt") as f:
            TAU = float(f.read().strip())
    except FileNotFoundError:
        TAU = 0.5  # placeholder until §11 calibrates one for real


class StartSessionRequest(BaseModel):
    prompt: str
    temperature: float = 1.0


class StartSessionResponse(BaseModel):
    session_id: int
    seed: int
    prompt: str
    temperature: float


@app.post("/session/start", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest):
    """The verifier dictates the seed — generated here, server-side, never
    accepted as client input. This is the fix to the reference
    implementation's backwards default the task calls out."""
    seed = secrets.randbits(63)
    session_id = db.create_session(req.prompt, seed, req.temperature)
    return StartSessionResponse(session_id=session_id, seed=seed, prompt=req.prompt, temperature=req.temperature)


class GenerateRequest(BaseModel):
    session_id: int
    max_tokens: int = 40


class GenerateResponse(BaseModel):
    output: str
    n_tokens: int


@app.post("/prover/generate", response_model=GenerateResponse)
def prover_generate(req: GenerateRequest):
    """Stands in for the prover's own serving stack. Uses the seed from the
    session the verifier created — the prover has to know the seed to
    decode as instructed; what it can't do is change what the verifier
    later checks against, because /verify never reads a seed from here."""
    session = db.get_session(req.session_id)
    prompt_tokens = encode(session["prompt"])
    ctx_len = prover_model.context_len
    seq = list(prompt_tokens)
    out = []
    for i in range(req.max_tokens):
        window = seq[-ctx_len:]
        if len(window) < ctx_len:
            window = [0] * (ctx_len - len(window)) + window
        logits = prover_model.forward_logits_only(np.array([window]))[0]
        tok = sampling.sample_token(logits, session["issued_seed"], len(prompt_tokens) + i, session["temperature"])
        out.append(tok)
        seq.append(tok)
    return GenerateResponse(output=decode(out), n_tokens=len(out))


class VerifyRequest(BaseModel):
    session_id: int
    claimed_output: str
    # Deliberately no `seed` field. See module docstring.


class VerifyResponse(BaseModel):
    verification_id: int
    passed: bool
    avg_deviation: float
    tau_used: float
    low_confidence: bool
    any_token_clipped: bool
    n_tokens: int


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest):
    session = db.get_session(req.session_id)
    prompt_tokens = encode(session["prompt"])
    claimed_tokens = encode(req.claimed_output)

    result = difr.verify(
        verifier_model,
        prompt_tokens,
        claimed_tokens,
        seed=session["issued_seed"],  # ALWAYS from the session record
        temperature=session["temperature"],
    )
    verification_id, passed = db.log_verification(req.session_id, req.claimed_output, result, TAU)

    return VerifyResponse(
        verification_id=verification_id,
        passed=passed,
        avg_deviation=result["avg_deviation"],
        tau_used=TAU,
        low_confidence=result["low_confidence"],
        any_token_clipped=any(t["clipped"] for t in result["per_token"]),
        n_tokens=result["n_tokens"],
    )


@app.get("/verification/{verification_id}")
def get_verification(verification_id: int):
    return db.fetch_verification(verification_id)
