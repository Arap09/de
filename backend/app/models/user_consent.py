from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base_class import Base


class UserConsent(Base):
    __tablename__ = "user_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    # Role at time of consent (IMPORTANT for legal traceability)
    role = Column(String, nullable=False)

    # Logical version of terms (e.g. agent_v1, staff_v1)
    terms_version = Column(String, nullable=False)

    accepted_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships (optional but useful)
    user = relationship("User", lazy="joined")
    tenant = relationship("Tenant", lazy="joined")

    __table_args__ = (
        # One active consent per user/tenant/role/terms
        UniqueConstraint(
            "user_id",
            "tenant_id",
            "role",
            "terms_version",
            name="uq_user_consent_role_terms",
        ),
    )
