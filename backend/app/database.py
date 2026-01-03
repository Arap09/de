import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Load .env from project root
# -------------------------------------------------------------------
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. PostgreSQL is required.")

if not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("Only PostgreSQL is supported. SQLite is disabled.")

# -------------------------------------------------------------------
# Engine
# -------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# -------------------------------------------------------------------
# Session
# -------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# -------------------------------------------------------------------
# Declarative Base (SINGLE SOURCE OF TRUTH)
# -------------------------------------------------------------------
Base = declarative_base()
