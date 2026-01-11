from app.core.roles import TenantRole


ROLE_HIERARCHY: dict[TenantRole, int] = {
    TenantRole.OWNER: 5,
    TenantRole.ADMIN: 4,
    TenantRole.MANAGER: 3,
    TenantRole.AGENT: 2,
    TenantRole.VIEWER: 1,
}


def role_at_least(
    user_role: TenantRole,
    required_role: TenantRole,
) -> bool:
    return ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[required_role]
