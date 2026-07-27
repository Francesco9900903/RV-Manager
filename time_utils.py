from datetime import datetime
from .config import ROME_TZ, UTC_TZ

def now_rome() -> datetime:
    return datetime.now(ROME_TZ)

def parse_db_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC_TZ)
    return parsed.astimezone(ROME_TZ)
