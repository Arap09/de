import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    # --------------------------------------------------
    # Primary Key
    # --------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --------------------------------------------------
    # Actor (nullable for system actions)
    # --------------------------------------------------
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------
    # Audit Details
    # --------------------------------------------------
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # IMPORTANT:
    # "metadata" is a reserved attribute name in SQLAlchemy Declarative.
    # Use a safe Python attribute name and (optionally) keep the DB column name as "metadata".
    event_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",  # DB column name (keep as-is to avoid migration if already created)
        JSONB,
        nullable=False,
        default=dict,  # Python-side default for new instances
    )

    # --------------------------------------------------
    # Timestamp
    # --------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
