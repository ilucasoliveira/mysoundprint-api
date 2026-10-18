from datetime import UTC, datetime, timedelta

import pytest


class FakePlay:
    """Minimal stand in for a ListeningHistory row."""

    def __init__(self, played_at: datetime, duration_ms: int = 200_000):
        self.played_at = played_at
        self.duration_ms = duration_ms


@pytest.fixture
def make_payload():
    """Build a top-items payload without touching the network."""

    def _make(entries: list[tuple[str, str, str]]) -> dict:
        return {
            "items": [
                {
                    "id": item_id,
                    "name": name,
                    "artists": [{"id": item_id, "name": name}],
                    "album": {"release_date": release_date},
                }
                for item_id, name, release_date in entries
            ]
        }

    return _make


@pytest.fixture
def plays() -> list[FakePlay]:
    base = datetime(2026, 9, 28, 21, 0, tzinfo=UTC)
    return [
        FakePlay(base + timedelta(days=day, hours=hour))
        for day in range(5)
        for hour in (0, 1, 2)
    ]
