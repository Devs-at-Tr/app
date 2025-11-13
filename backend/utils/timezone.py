from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def now_ist() -> datetime:
    """Return current time in Asia/Kolkata timezone."""
    return utc_now().astimezone(IST)
