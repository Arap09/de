import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base  # single authoritative Base


# --------------------------------------------------
# Tier ENUM (Python)
# --------------------------------------------------
class TierEnum(str, enum.Enum):
    sungura = "sungura"
    swara = "swara"
    ndovu = "ndovu"


# --------------------------------------------------
# PostgreSQL ENUM binding (CRITICAL)
# --------------------------------------------------
tier_enum = SAEnum(
    TierEnum,
    name="tierenum",
    native_enum=True,
    create_type=False,   # DO NOT recreate ENUM
    validate_strings=True,
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
        UniqueConstraint("referral_code", name="ix_users_referral_code"),
    )

    # --------------------------------------------------
    # Primary Key
    # --------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # --------------------------------------------------
    # Identity (nullable → post-login completion)
    # --------------------------------------------------
    first_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
    )

    country_code: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
    )

    # --------------------------------------------------
    # Authentication (magic-code compatible)
    # --------------------------------------------------
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # --------------------------------------------------
    # Authorization / Role
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
        tier_enum,
        nullable=False,
        default=TierEnum.sungura,
    )

    trial_starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    trial_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    # --------------------------------------------------
    # Referral
    # --------------------------------------------------
    referral_code: Mapped[str] = mapped_column(
        String(12),
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
