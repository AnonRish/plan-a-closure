"""Shared pytest fixtures.

Sets FV_API_KEYS, FV_DATA_DIR, and FV_KEY_DIR to isolated, session-scoped
temp locations BEFORE any test module imports frontier_verify.api.main --
conftest.py's module-level code runs at collection time, ahead of test
imports, so this ordering is reliable without needing import-order tricks
inside the app itself (auth.py and store.py both read their env vars
lazily/at-construction specifically so this works).

TEST_API_KEY holds ALL FOUR roles (see frontier_verify/api/auth.py) so
that existing tests, which mostly aren't testing role RESTRICTION
specifically, don't need to know about roles at all. Tests that DO need
to exercise authorization failures (tests/unit/test_authorization.py)
mint their own separate, deliberately narrower keys by manipulating
FV_API_KEYS within the test itself.
"""
from __future__ import annotations

import os
import tempfile

TEST_API_KEY = "test-key-for-pytest"
_ALL_ROLES = "PROVER|POLICY_AUTHORITY|ADMINISTRATOR|AUDITOR"
os.environ.setdefault("FV_API_KEYS", f"{TEST_API_KEY}:{_ALL_ROLES}")
os.environ.setdefault("FV_DATA_DIR", tempfile.mkdtemp(prefix="frontier-verify-test-data-"))
os.environ.setdefault("FV_KEY_DIR", tempfile.mkdtemp(prefix="frontier-verify-test-keys-"))

import pytest


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-Api-Key": TEST_API_KEY}
