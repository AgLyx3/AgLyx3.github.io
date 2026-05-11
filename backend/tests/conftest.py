"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from app.services.db import init_db


@pytest.fixture(scope="session", autouse=True)
def test_db():
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "test.db"

    original_db = os.environ.get("DATABASE_URL")
    original_analytics = os.environ.get("ANALYTICS_WRITE_ENABLED")

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ANALYTICS_WRITE_ENABLED"] = "true"
    init_db()

    yield

    if original_db is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original_db

    if original_analytics is None:
        os.environ.pop("ANALYTICS_WRITE_ENABLED", None)
    else:
        os.environ["ANALYTICS_WRITE_ENABLED"] = original_analytics

    tmpdir.cleanup()
