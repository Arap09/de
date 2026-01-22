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

from app.db.base import Base


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
    create_type=False,   # DO NOT recreate ENUM in migrations
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
    first_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    email: Mapped[str] = mapped_column(String(255), nullable=False)

    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
    )

    country_code: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # --------------------------------------------------
    # Authentication (magic-code compatible)
    # --------------------------------------------------
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --------------------------------------------------
    # Magic Code (for email-first authentication)
    # --------------------------------------------------
    magic_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    magic_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --------------------------------------------------
    # Authorization / Role
    # --------------------------------------------------
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="client")

    # --------------------------------------------------
    # Subscription / Tier
    # --------------------------------------------------
    tier: Mapped[TierEnum] = mapped_column(
        tier_enum,
        nullable=False,
        default=TierEnum.sungura,
    )

    trial_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --------------------------------------------------
    # Referral
    # --------------------------------------------------
    referral_code: Mapped[str | None] = mapped_column(
        String(12),
        nullable=True,
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
    # Preferences / Compliance (latest state shortcuts)
    # --------------------------------------------------
    accepts_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=False,   # opt-in
        nullable=False,
    )

    accepted_terms: Mapped[bool] = mapped_column(
        Boolean,
        default=False,   # explicit acceptance required
        nullable=False,
    )

    terms_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notifications_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --------------------------------------------------
    # Relationships (consent/audit)
    # Your current UserConsent model does not declare back_populates.
    # Keep this one-way relationship to avoid mapper configuration errors.
    # --------------------------------------------------
    consents = relationship(
        "UserConsent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # --------------------------------------------------
    # Timestamps
    # --------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
