"""Real PostgreSQL logging — not simulated. Schema:

sessions: one row per (prompt, verifier-issued seed) the verifier has
          committed to. The seed lives here, set once, never updated.
verifications: one row per /verify call against a session, including the
          full per-token breakdown (so a clipped token is visible in the
          log, not silently averaged away) and the low-confidence flag.
"""
import json
import psycopg2
import psycopg2.extras

DSN = "dbname=difr_verification user=postgres password=verifier host=127.0.0.1 port=5432"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    issued_seed BIGINT NOT NULL,
    temperature REAL NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS verifications (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    claimed_output TEXT NOT NULL,
    n_tokens INTEGER NOT NULL,
    avg_deviation REAL NOT NULL,
    tau_used REAL NOT NULL,
    passed BOOLEAN NOT NULL,
    low_confidence BOOLEAN NOT NULL,
    any_token_clipped BOOLEAN NOT NULL,
    per_token_detail JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def get_conn():
    return psycopg2.connect(DSN)


def init_schema():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()


def create_session(prompt: str, issued_seed: int, temperature: float) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (prompt, issued_seed, temperature) VALUES (%s, %s, %s) RETURNING id",
                (prompt, issued_seed, temperature),
            )
            session_id = cur.fetchone()[0]
        conn.commit()
    return session_id


def get_session(session_id: int):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
            return cur.fetchone()


def log_verification(session_id: int, claimed_output: str, result: dict, tau: float):
    any_clipped = any(t["clipped"] for t in result["per_token"])
    passed = result["avg_deviation"] <= tau
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO verifications
                   (session_id, claimed_output, n_tokens, avg_deviation, tau_used,
                    passed, low_confidence, any_token_clipped, per_token_detail)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (
                    session_id,
                    claimed_output,
                    result["n_tokens"],
                    result["avg_deviation"],
                    tau,
                    passed,
                    result["low_confidence"],
                    any_clipped,
                    json.dumps(result["per_token"]),
                ),
            )
            row_id = cur.fetchone()[0]
        conn.commit()
    return row_id, passed


def fetch_verification(row_id: int):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM verifications WHERE id = %s", (row_id,))
            return cur.fetchone()
