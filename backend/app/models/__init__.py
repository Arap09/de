# Centralized model registry
# Import ALL SQLAlchemy models here so they are registered on Base.metadata

from app.models.user import User
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership

# Consent
from app.models.user_consent import UserConsent

# Invitations (Tenant)
from app.models.tenant_invitation import TenantInvitation

# Existing models you mentioned (register them as well)
from app.models.audit_log import AuditLog
from app.models.email_verification import EmailVerification
from app.models.referral import Referral

# Platform / Sales (NEW)
from app.models.platform_membership import PlatformMembership
from app.models.platform_invitation import PlatformInvitation
from app.models.salesperson_profile import SalespersonProfile
from app.models.referral_commission import ReferralCommission

# NOTE:
# As you add new models, they MUST be imported here.
