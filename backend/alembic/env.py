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
# Explicitly load .env BEFORE any app imports
# -------------------------------------------------------------------
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

# -------------------------------------------------------------------
# Read DATABASE_URL
# -------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. PostgreSQL (Neon) is required."
    )

# -------------------------------------------------------------------
# Normalize DATABASE_URL for Alembic (sync psycopg2 only)
# -------------------------------------------------------------------
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql+psycopg2://",
        1,
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1,
    )

if "ssl=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace(
        "ssl=require",
        "sslmode=require",
    )

if not DATABASE_URL.startswith("postgresql+psycopg2://"):
    raise RuntimeError(
        "Only PostgreSQL is supported. SQLite is disabled."
    )

# -------------------------------------------------------------------
# Import metadata AND MODELS
# -------------------------------------------------------------------
from app.database import Base  # noqa: E402
import app.models  # noqa: E402  ✅ CRITICAL FIX

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
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL},
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
