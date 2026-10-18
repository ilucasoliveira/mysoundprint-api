from collections import Counter
from datetime import UTC, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

PERIODS = (
    ("night", range(0, 6)),
    ("morning", range(6, 12)),
    ("afternoon", range(12, 18)),
    ("evening", range(18, 24)),
)


def resolve_timezone(tz_name: str) -> ZoneInfo:
    """Turn a timezone name into a ZoneInfo, or raise ValueError.

    ZoneInfo reads the IANA database from the operating system. Windows has
    no such database and the slim Docker images do not ship one either, so
    the `tzdata` package is a hard requirement, not a convenience.
    """
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"unknown timezone: {tz_name}") from error


def _period_of(hour: int) -> str:
    for name, hours in PERIODS:
        if hour in hours:
            return name
    return "night"


def temporal_patterns(plays: list, tz_name: str = "UTC") -> dict:
    """Distribution of listening across hours of the day and days of the week.

    `plays` is a list of objects carrying `played_at` (an aware datetime) and
    `duration_ms`. Timestamps are stored in UTC and converted here, because
    "when do I listen" is a question about local time, not UTC.
    """
    tz = resolve_timezone(tz_name)

    hours = Counter()
    weekdays = Counter()
    periods = Counter()
    total_ms = 0

    for play in plays:
        played_at = play.played_at
        if played_at.tzinfo is None:
            played_at = played_at.replace(tzinfo=UTC)
        local = played_at.astimezone(tz)

        hours[local.hour] += 1
        weekdays[local.weekday()] += 1
        periods[_period_of(local.hour)] += 1
        total_ms += play.duration_ms or 0

    total = len(plays)
    if total == 0:
        return {
            "total_plays": 0,
            "timezone": tz_name,
            "by_hour": [],
            "by_weekday": [],
            "by_period": [],
            "peak_hour": None,
            "peak_weekday": None,
            "total_minutes": 0,
            "first_play": None,
            "last_play": None,
        }

    by_hour = [
        {
            "hour": hour,
            "count": hours.get(hour, 0),
            "percentage": round(hours.get(hour, 0) / total * 100, 1),
        }
        for hour in range(24)
    ]

    by_weekday = [
        {
            "weekday": index,
            "name": WEEKDAY_NAMES[index],
            "count": weekdays.get(index, 0),
            "percentage": round(weekdays.get(index, 0) / total * 100, 1),
        }
        for index in range(7)
    ]

    by_period = [
        {
            "period": name,
            "count": periods.get(name, 0),
            "percentage": round(periods.get(name, 0) / total * 100, 1),
        }
        for name, _ in PERIODS
    ]

    peak_hour = hours.most_common(1)[0][0]
    peak_weekday = weekdays.most_common(1)[0][0]
    timestamps = [play.played_at for play in plays]

    return {
        "total_plays": total,
        "timezone": tz_name,
        "by_hour": by_hour,
        "by_weekday": by_weekday,
        "by_period": by_period,
        "peak_hour": peak_hour,
        "peak_weekday": WEEKDAY_NAMES[peak_weekday],
        "total_minutes": round(total_ms / 60000, 1),
        "first_play": min(timestamps).isoformat(),
        "last_play": max(timestamps).isoformat(),
    }


def listening_streak(plays: list, tz_name: str = "UTC") -> dict:
    """Longest and current run of consecutive days with at least one play."""
    tz = resolve_timezone(tz_name)
    days = sorted({play.played_at.astimezone(tz).date() for play in plays})

    if not days:
        return {"longest_streak": 0, "current_streak": 0, "active_days": 0}

    longest = current = 1
    for previous, day in pairwise(days):
        if day - previous == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return {
        "longest_streak": longest,
        "current_streak": current,
        "active_days": len(days),
    }
