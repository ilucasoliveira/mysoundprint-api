import pytest

from app.services.stats import (
    compare_time_ranges,
    decade_distribution,
    listening_concentration,
)


class TestDecadeDistribution:
    def test_groups_tracks_by_decade(self, make_payload):
        payload = make_payload(
            [
                ("a", "A", "1981-01-01"),
                ("b", "B", "1999"),
                ("c", "C", "2004-11-12"),
                ("d", "D", "2009-01-01"),
            ]
        )
        result = decade_distribution(payload)

        assert result["total_tracks"] == 4
        assert [entry["decade"] for entry in result["decades"]] == [1980, 1990, 2000]

    def test_handles_year_only_release_dates(self, make_payload):
        """Spotify sends "1999" when release_date_precision is "year"."""
        payload = make_payload([("a", "A", "1999")])
        assert decade_distribution(payload)["decades"][0]["decade"] == 1990

    def test_percentages_sum_to_one_hundred(self, make_payload):
        payload = make_payload(
            [(str(index), "X", "2013-01-01") for index in range(3)]
        )
        total = sum(
            entry["percentage"] for entry in decade_distribution(payload)["decades"]
        )
        assert total == pytest.approx(100, abs=0.5)

    def test_decades_are_chronological(self, make_payload):
        payload = make_payload(
            [("a", "A", "2020"), ("b", "B", "1970"), ("c", "C", "1990")]
        )
        decades = [entry["decade"] for entry in decade_distribution(payload)["decades"]]
        assert decades == sorted(decades)


class TestListeningConcentration:
    def test_counts_distinct_primary_artists(self, make_payload):
        payload = make_payload(
            [
                ("a", "Taylor Swift", "2020"),
                ("b", "Taylor Swift", "2020"),
                ("c", "Katy Perry", "2010"),
            ]
        )
        result = listening_concentration(payload)

        assert result["total_tracks"] == 3
        assert result["distinct_artists"] == 2
        assert result["top_artists"][0]["name"] == "Taylor Swift"
        assert result["top_artists"][0]["count"] == 2

    def test_share_is_capped_at_one_hundred(self, make_payload):
        payload = make_payload([("a", "Solo", "2020"), ("b", "Solo", "2020")])
        assert listening_concentration(payload)["top_3_share"] == 100.0


class TestCompareTimeRanges:
    def test_detects_entries_and_drops(self, make_payload):
        baseline = make_payload([("ts", "Taylor", "2020"), ("ag", "Ariana", "2020")])
        current = make_payload([("ts", "Taylor", "2020"), ("sc", "Sabrina", "2020")])

        result = compare_time_ranges(baseline, current)

        assert [entry["name"] for entry in result["entered"]] == ["Sabrina"]
        assert [entry["name"] for entry in result["dropped"]] == ["Ariana"]
        assert result["stable_count"] == 1

    def test_climbed_and_fell_are_separate_and_positive(self, make_payload):
        baseline = make_payload(
            [("a", "A", "2020"), ("b", "B", "2020"), ("c", "C", "2020")]
        )
        current = make_payload(
            [("c", "C", "2020"), ("a", "A", "2020"), ("b", "B", "2020")]
        )

        result = compare_time_ranges(baseline, current)

        assert [entry["name"] for entry in result["climbed"]] == ["C"]
        assert result["climbed"][0]["change"] == 2
        assert all(entry["change"] > 0 for entry in result["fell"])

    def test_unchanged_items_are_counted_not_listed(self, make_payload):
        payload = make_payload([("a", "A", "2020"), ("b", "B", "2020")])
        result = compare_time_ranges(payload, payload)

        assert result["unchanged_count"] == 2
        assert result["climbed"] == []
        assert result["fell"] == []
