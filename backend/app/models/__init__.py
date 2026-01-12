# Centralized model registry
# Import ALL SQLAlchemy models here so they are registered on Base.metadata

from app.models.user import User
from app.models.tenant_membership import TenantMembership

# NOTE:
# As you add new models (Tenant, Role, Permission, etc.),
# they MUST be imported here.
