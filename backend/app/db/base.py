from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy models.

    Business logic (auth, referrals, billing, etc.)
    MUST NOT be placed here.
    """
    pass
