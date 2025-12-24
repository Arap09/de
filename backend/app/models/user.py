import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class TierEnum(str, enum.Enum):
    sungura = "sungura"
    swara = "swara"
    ndovu = "ndovu"


class User(Base):
    __tablename__ = "users"

    # --------------------------------------------------
    # Primary Key
    # --------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )

    country_code: Mapped[str] = mapped_column(String(5), nullable=False)

    # --------------------------------------------------
    # Authentication
    # --------------------------------------------------
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --------------------------------------------------
    # Authorization / Role
    # client | salesperson | admin | super_admin
    # --------------------------------------------------
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="client",
    )

    # --------------------------------------------------
    # Subscription / Tier
    # --------------------------------------------------
    tier: Mapped[TierEnum] = mapped_column(
        Enum(TierEnum),
        nullable=False,
        default=TierEnum.sungura,
    )

    trial_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --------------------------------------------------
    # Referral (salesperson-owned)
    # --------------------------------------------------
    referral_code: Mapped[str] = mapped_column(
        String(12),
        unique=True,
        index=True,
        nullable=False,
    )

    referred_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    referrer = relationship(
        "User",
        remote_side="User.id",
        lazy="joined",
    )

    # --------------------------------------------------
    # Preferences / Compliance
    # --------------------------------------------------
    accepts_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    accepted_terms: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    # --------------------------------------------------
    # Timestamps
    # --------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
