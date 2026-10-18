import json
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data"


class DemoPlay:
    """Mirrors the attributes temporal_stats reads from a ListeningHistory
    row, so the same pure functions serve both real and demo data."""

    __slots__ = ("artist_name", "duration_ms", "played_at", "track_name")

    def __init__(
        self,
        played_at: datetime,
        duration_ms: int,
        track_name: str,
        artist_name: str,
    ):
        self.played_at = played_at
        self.duration_ms = duration_ms
        self.track_name = track_name
        self.artist_name = artist_name


@lru_cache(maxsize=16)
def load_snapshot(name: str) -> dict:
    """Read a stored Spotify response from disk.

    This is the seam that makes demo mode possible: the statistics functions
    take a payload and never ask where it came from.
    """
    path = DEMO_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"demo snapshot '{name}' not found, run scripts/build_demo_snapshot.py first"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def demo_top_items(item_type: str, time_range: str) -> dict:
    return load_snapshot(f"top_{item_type}_{time_range}")


def demo_history(days: int = 90) -> list[DemoPlay]:
    """Build a listening history anchored to today, so the demo always shows
    a recent window instead of a frozen date in the past."""
    payload = load_snapshot("recently_played")
    now = datetime.now(UTC)

    plays: list[DemoPlay] = []
    for offset, item in enumerate(payload.get("items", [])):
        track = item.get("track") or item.get("item") or {}
        artists = track.get("artists") or [{}]
        played_at = now - timedelta(hours=offset * 7, minutes=offset * 13)
        if (now - played_at).days > days:
            continue
        plays.append(
            DemoPlay(
                played_at=played_at,
                duration_ms=track.get("duration_ms") or 0,
                track_name=track.get("name") or "",
                artist_name=artists[0].get("name") or "",
            )
        )
    return plays
