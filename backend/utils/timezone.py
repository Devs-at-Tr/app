from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    """Return current time in Asia/Kolkata timezone."""
    return datetime.now(timezone.utc).astimezone(IST)
