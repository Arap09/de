"""
Compatibility shim.

Some models import Base from `app.db.base_class`, but the project may define Base
elsewhere (e.g. `app.db.base`). Keep this module to avoid import breakage.
"""

try:
    # Most common layout
    from app.db.base import Base  # type: ignore
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "Could not import Base. Expected `app/db/base.py` to define Base.\n"
        "Either create `app/db/base.py` with Base, or update models to import Base "
        "from the correct module."
    ) from e

__all__ = ["Base"]
