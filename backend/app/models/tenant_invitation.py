import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class TenantInvitation(Base):
    """
    Invitation to join a tenant with a specific role.

    Design principles:
    - Tenant-scoped
    - Role-scoped
    - Token-based acceptance
    - Supports revoke/expire/audit
    """

    __tablename__ = "tenant_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    inviter_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Store normalized email (lowercase). Always compare normalized.
    email = Column(String, nullable=False)

    # Expected values: ADMIN, MANAGER, AGENT, SALES
    role = Column(String, nullable=False)

    # High-entropy, unique token used to accept invite
    token = Column(String, nullable=False, unique=True, index=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Optional relationships (useful in admin UI / audit)
    tenant = relationship("Tenant", lazy="joined")
    inviter = relationship("User", lazy="joined")

    __table_args__ = (
        # Speed up common queries (pending invites per tenant/email)
        Index(
            "ix_tenant_invitations_tenant_email_pending",
            "tenant_id",
            "email",
            postgresql_where=(accepted_at.is_(None) & revoked_at.is_(None)),
        ),
        Index(
            "ix_tenant_invitations_tenant_pending",
            "tenant_id",
            postgresql_where=(accepted_at.is_(None) & revoked_at.is_(None)),
        ),
    )
