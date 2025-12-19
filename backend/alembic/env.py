from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Ensure backend/ is on PYTHONPATH so `app.*` imports work
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

# -------------------------------------------------------------------
# Load environment variables from .env
# -------------------------------------------------------------------
load_dotenv()

# -------------------------------------------------------------------
# Alembic configuration
# -------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------------------------
# Import SQLAlchemy Base (ALL models must be imported via Base)
# -------------------------------------------------------------------
from app.database import Base  # noqa: E402

target_metadata = Base.metadata

# -------------------------------------------------------------------
# Database URL resolver (PostgreSQL ONLY)
# -------------------------------------------------------------------
def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. PostgreSQL is required for POSTIKA."
        )

    if database_url.startswith("sqlite"):
        raise RuntimeError(
            "SQLite is not allowed. POSTIKA must use PostgreSQL."
        )

    return database_url

# -------------------------------------------------------------------
# Offline migrations
# -------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# -------------------------------------------------------------------
# Online migrations
# -------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": get_database_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
