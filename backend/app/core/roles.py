# app/core/roles.py
from enum import Enum


class PlatformRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    PLATFORM_ADMIN = "platform_admin"

    # Sales / salesperson platform actor
    # - "SALES" matches your consent policy key mapping in app/api/deps.py
    # - "SALESPERSON" is an alias for developer ergonomics (both work)
    SALES = "sales"
    SALESPERSON = "sales"


class TenantRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"
