"""
Posting-time parsing with board-local dates and explicit precision.

Every helper returns a PostedTime: the board-local date, an ISO 8601 timestamp
with UTC offset, and how precise that timestamp is. Board-local time comes from
zoneinfo, never the container clock, so a UTC container still dates an early
morning Melbourne post correctly.
"""

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, NamedTuple, Optional
from zoneinfo import ZoneInfo

Precision = Literal["minute", "hour", "day"]

_BOARD_TZ = {
    "AU": ZoneInfo("Australia/Melbourne"),
    "NZ": ZoneInfo("Pacific/Auckland"),
}


class PostedTime(NamedTuple):
    date: Optional[str]
    ts: Optional[str]
    precision: Optional[Precision]

    def as_fields(self) -> dict:
        """Keyword arguments for JobPosting / _build_job_posting."""
        return {"posted_at": self.date, "posted_at_ts": self.ts, "posted_at_precision": self.precision}


EMPTY = PostedTime(None, None, None)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def board_tz(country: Literal["AU", "NZ"]) -> ZoneInfo:
    return _BOARD_TZ[country]


def _local_midnight(day: date, tz: ZoneInfo) -> PostedTime:
    midnight = datetime.combine(day, time.min, tzinfo=tz)
    return PostedTime(day.isoformat(), midnight.isoformat(), "day")


def from_relative(
    text: str, country: Literal["AU", "NZ"] = "AU", now: Optional[datetime] = None
) -> PostedTime:
    """Parse Seek-style relative text: "Posted 25m ago", "3h", "2d", "30+d", "2d/1h"."""
    if not text:
        return EMPTY
    clean = text.replace("Posted", "").replace("ago", "").strip().lower()
    days = re.search(r"(\d+)\+?d", clean)
    hours = re.search(r"(\d+)h", clean)
    minutes = re.search(r"(\d+)m", clean)
    if not (days or hours or minutes):
        return EMPTY

    tz = board_tz(country)
    local_now = (now or _utcnow()).astimezone(tz)
    delta = timedelta(
        days=int(days.group(1)) if days else 0,
        hours=int(hours.group(1)) if hours else 0,
        minutes=int(minutes.group(1)) if minutes else 0,
    )
    posted = (local_now - delta).replace(second=0, microsecond=0)

    if minutes:
        precision: Precision = "minute"
    elif hours:
        precision = "hour"
    else:
        return _local_midnight(posted.date(), tz)
    return PostedTime(posted.date().isoformat(), posted.isoformat(), precision)


def from_iso(value: Optional[str], country: Literal["AU", "NZ"] = "AU") -> PostedTime:
    """Parse an ISO date or datetime; a time component gives minute precision."""
    if not value:
        return EMPTY
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return EMPTY

    tz = board_tz(country)
    if len(text) <= 10:
        return _local_midnight(parsed.date(), tz)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    local = parsed.astimezone(tz).replace(second=0, microsecond=0)
    return PostedTime(local.date().isoformat(), local.isoformat(), "minute")


def from_date(
    value: "str | date | datetime | None", country: Literal["AU", "NZ"] = "AU"
) -> PostedTime:
    """Day-precision PostedTime from a date, datetime, or YYYY-MM-DD string."""
    if value is None:
        return EMPTY
    if isinstance(value, datetime):
        day = value.date()
    elif isinstance(value, date):
        day = value
    else:
        try:
            day = date.fromisoformat(str(value).strip()[:10])
        except ValueError:
            return EMPTY
    return _local_midnight(day, board_tz(country))
