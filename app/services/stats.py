from collections import Counter


def _extract_decade(release_date: str) -> int:
    year = int(release_date[:4])
    return (year // 10) * 10


def decade_distribution(data: dict) -> dict:
    items = data["items"]
    decades = [_extract_decade(item["album"]["release_date"]) for item in items]

    total = len(decades)
    counter = Counter(decades)

    distribution = [
        {
            "decade": decade,
            "count": count,
            "percentage": round(count / total * 100, 1),
        }
        for decade, count in sorted(counter.items())
    ]

    return {"total_tracks": total, "decades": distribution}
