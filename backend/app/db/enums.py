import enum
from sqlalchemy import Enum as SAEnum

class TierEnum(enum.Enum):
    sungura = "sungura"
    swara = "swara"
    ndovu = "ndovu"


tier_enum = SAEnum(
    TierEnum,
    name="tierenum",
    native_enum=True,
    create_type=False,   # 🔴 CRITICAL: do NOT recreate ENUM
    validate_strings=True
)
