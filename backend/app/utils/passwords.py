import re
import secrets
import string


PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def validate_password_rules(password: str) -> None:
    """
    Enforce strong password rules.
    """
    if not PASSWORD_REGEX.match(password):
        raise ValueError(
            "Password must be at least 8 characters long and include "
            "uppercase, lowercase, digit, and special character."
        )


def generate_password() -> str:
    """
    Generate a strong random password that satisfies validation rules.
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*"

    while True:
        password = "".join(secrets.choice(chars) for _ in range(12))
        if PASSWORD_REGEX.match(password):
            return password
