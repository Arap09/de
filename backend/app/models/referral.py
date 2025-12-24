import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Referral(Base):
    __tablename__ = "referrals"

    # --------------------------------------------------
    # Primary Key
    # --------------------------------------------------
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # --------------------------------------------------
    # Relationships
    # --------------------------------------------------
    referrer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    referred_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # --------------------------------------------------
    # Reward (Option B – uniform, snapshot at creation)
    # --------------------------------------------------
    reward_amount_kes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reward_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --------------------------------------------------
    # Timestamps
    # --------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
