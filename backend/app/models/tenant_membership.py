import uuid
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base import Base
from app.core.roles import TenantRole


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(
        Enum(TenantRole, name="tenant_role_enum"),
        nullable=False,
    )

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    created_by = Column(PG_UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "tenant_id",
            name="uq_user_tenant_membership",
        ),
    )
