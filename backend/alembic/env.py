# app/alembic/env.py
import sys
import os
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Resolve backend base directory and ensure PYTHONPATH
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# -------------------------------------------------------------------
# Explicitly load .env (Alembic runs outside app context)
# -------------------------------------------------------------------
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

# -------------------------------------------------------------------
# Read SYNC database URL ONLY
# -------------------------------------------------------------------
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC")

if not DATABASE_URL_SYNC:
    raise RuntimeError(
        "DATABASE_URL_SYNC is not set. Alembic requires a sync PostgreSQL URL."
    )

if "asyncpg" in DATABASE_URL_SYNC:
    raise RuntimeError(
        "DATABASE_URL_SYNC must NOT use asyncpg."
    )

# -------------------------------------------------------------------
# Import metadata AND MODELS
# -------------------------------------------------------------------
from app.database import Base  # noqa: E402
import app.models  # noqa: E402

# -------------------------------------------------------------------
# Alembic configuration
# -------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# -------------------------------------------------------------------
# Migration runners
# -------------------------------------------------------------------
def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL_SYNC,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL_SYNC},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
