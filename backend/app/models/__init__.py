# Centralized model registry
# Import ALL SQLAlchemy models here so they are registered on Base.metadata

from app.models.user import User
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership

# Consent
from app.models.user_consent import UserConsent

# Invitations
from app.models.tenant_invitation import TenantInvitation

# Existing models you mentioned (register them as well)
from app.models.audit_log import AuditLog
from app.models.email_verification import EmailVerification
from app.models.referral import Referral

# NOTE:
# As you add new models, they MUST be imported here.
