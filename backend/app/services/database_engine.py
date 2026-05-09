"""Database engine helpers for SQLite and Postgres runtimes."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any

from app.config import get_settings


DatabaseDialect = str


def database_url() -> str:
    return get_settings().database_url.strip()


def database_dialect(url: str | None = None) -> DatabaseDialect:
    raw = (url or database_url()).strip().lower()
    if raw.startswith("postgres://") or raw.startswith("postgresql://"):
        return "postgres"
    return "sqlite"


def sqlite_db_path(url: str | None = None) -> Path:
    raw = (url or database_url()).strip()
    if raw.startswith("sqlite:///"):
        relative = raw.removeprefix("sqlite:///")
        return Path(__file__).resolve().parents[3] / relative
    return Path(__file__).resolve().parents[2] / "data" / "app.db"


def _convert_placeholders(query: str) -> str:
    return query.replace("?", "%s")


class SyncDatabaseConnection:
    def __init__(self, raw: Any, dialect: DatabaseDialect) -> None:
        self._raw = raw
        self.dialect = dialect

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()):
        if self.dialect == "postgres":
            return self._raw.execute(_convert_placeholders(query), params)
        return self._raw.execute(query, params)

    def executemany(self, query: str, seq_of_params: list[tuple[Any, ...]]):
        if self.dialect == "postgres":
            return self._raw.executemany(_convert_placeholders(query), seq_of_params)
        return self._raw.executemany(query, seq_of_params)

    def executescript(self, script: str):
        if self.dialect == "postgres":
            cursor = None
            for statement in script.split(";"):
                cleaned = statement.strip()
                if not cleaned:
                    continue
                cursor = self._raw.execute(cleaned)
            return cursor
        return self._raw.executescript(script)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()


@contextmanager
def open_database_connection():
    dialect = database_dialect()
    if dialect == "postgres":
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "Postgres support requires psycopg. Install backend dependencies before running with a postgres DATABASE_URL."
            ) from exc

        conn = psycopg.connect(database_url(), row_factory=dict_row)
    else:
        path = sqlite_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row

    wrapped = SyncDatabaseConnection(conn, dialect)
    try:
        yield wrapped
    finally:
        wrapped.close()
