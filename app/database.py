import os

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import create_engine

DEFAULT_DATABASE_URL = "sqlite:///echo_nest.db"
_ENGINE_CACHE: dict[str, Engine] = {}


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine() -> Engine:
    """Return a cached SQLModel engine for the configured database URL."""
    db_url = get_database_url()
    engine = _ENGINE_CACHE.get(db_url)
    if engine is not None:
        return engine

    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite:") else {}
    engine = create_engine(db_url, echo=False, connect_args=connect_args)
    _ENGINE_CACHE[db_url] = engine
    return engine


def ensure_schema() -> None:
    """Backfill lightweight schema changes for existing SQLite databases."""
    engine = get_engine()
    db_url = get_database_url()
    if not db_url.startswith("sqlite:"):
        return

    with engine.begin() as conn:
        table_names = {
            row[0]
            for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        }
        if "entry" not in table_names:
            return

        columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info('entry')"))
        }
        column_updates = {
            "emotion_state": "ALTER TABLE entry ADD COLUMN emotion_state VARCHAR DEFAULT 'calm'",
            "sleep_hours": "ALTER TABLE entry ADD COLUMN sleep_hours FLOAT",
            "interaction_level": "ALTER TABLE entry ADD COLUMN interaction_level INTEGER",
            "screen_time_hours": "ALTER TABLE entry ADD COLUMN screen_time_hours FLOAT",
        }
        for column_name, ddl in column_updates.items():
            if column_name not in columns:
                conn.execute(text(ddl))


def reset_engine_cache() -> None:
    """Dispose cached engines and clear the engine cache."""
    for engine in _ENGINE_CACHE.values():
        engine.dispose()
    _ENGINE_CACHE.clear()
