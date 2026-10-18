from datetime import UTC, datetime, timedelta

from app.services.temporal_stats import listening_streak, temporal_patterns


def fake_play(played_at: datetime, duration_ms: int = 0):
    return type(
        "FakePlay", (), {"played_at": played_at, "duration_ms": duration_ms}
    )()


class TestTemporalPatterns:
    def test_empty_history_does_not_divide_by_zero(self):
        result = temporal_patterns([])
        assert result["total_plays"] == 0
        assert result["peak_hour"] is None

    def test_buckets_cover_every_hour_and_weekday(self, plays):
        result = temporal_patterns(plays)
        assert len(result["by_hour"]) == 24
        assert len(result["by_weekday"]) == 7

    def test_converts_utc_to_the_requested_timezone(self):
        """21:00 UTC is 18:00 in Sao Paulo, so the peak has to shift."""
        play = fake_play(datetime(2026, 9, 28, 21, 0, tzinfo=UTC))

        assert temporal_patterns([play], "UTC")["peak_hour"] == 21
        assert temporal_patterns([play], "America/Sao_Paulo")["peak_hour"] == 18

    def test_total_minutes_sums_durations(self):
        play = fake_play(datetime(2026, 9, 28, tzinfo=UTC), 180_000)
        assert temporal_patterns([play, play])["total_minutes"] == 6.0


class TestListeningStreak:
    def test_counts_consecutive_days(self, plays):
        assert listening_streak(plays)["longest_streak"] == 5

    def test_gap_breaks_the_streak(self):
        base = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
        items = [fake_play(base + timedelta(days=day)) for day in (0, 1, 2, 10, 11)]

        result = listening_streak(items)

        assert result["longest_streak"] == 3
        assert result["current_streak"] == 2
        assert result["active_days"] == 5


class TestResolveTimezone:
    def test_rejects_an_unknown_timezone(self):
        """Without this, a bad query param would surface as a 500."""
        import pytest

        from app.services.temporal_stats import resolve_timezone

        with pytest.raises(ValueError):
            resolve_timezone("Mars/Olympus_Mons")
