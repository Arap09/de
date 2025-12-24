import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    # --------------------------------------------------
    # Primary Key
    # --------------------------------------------------
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # --------------------------------------------------
    # Relationship
    # --------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --------------------------------------------------
    # Verification Code
    # --------------------------------------------------
    code: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # --------------------------------------------------
    # Timestamp
    # --------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
