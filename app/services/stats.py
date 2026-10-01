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


def _build_position_map(data: dict) -> dict:
    return {
        item["id"]: position for position, item in enumerate(data["items"], start=1)
    }


def _build_name_map(data: dict) -> dict[str, str]:
    return {item["id"]: item["name"] for item in data["items"]}


def compare_time_ranges(baseline: dict, current: dict) -> dict:
    baseline_positions = _build_position_map(baseline)
    current_positions = _build_position_map(current)
    names = _build_name_map(baseline) | _build_name_map(current)

    baseline_ids = set(baseline_positions)
    current_ids = set(current_positions)

    entered = [
        {"id": item_id, "name": names[item_id], "position": current_positions[item_id]}
        for item_id in sorted(current_ids - baseline_ids, key=current_positions.get)
    ]

    dropped = [
        {"id": item_id, "name": names[item_id], "position": baseline_positions[item_id]}
        for item_id in sorted(baseline_ids - current_ids, key=baseline_positions.get)
    ]

    climbed = []
    fell = []
    unchanged = 0

    for item_id in baseline_ids & current_ids:
        before = baseline_positions[item_id]
        after = current_positions[item_id]
        change = before - after

        if change == 0:
            unchanged += 1
            continue

        entry = {
            "id": item_id,
            "name": names[item_id],
            "from_position": before,
            "to_position": after,
            "change": abs(change),
        }

        if change > 0:
            climbed.append(entry)
        else:
            fell.append(entry)

    climbed.sort(key=lambda entry: entry["change"], reverse=True)
    fell.sort(key=lambda entry: entry["change"], reverse=True)

    return {
        "entered": entered,
        "dropped": dropped,
        "climbed": climbed,
        "fell": fell,
        "unchanged_count": unchanged,
        "stable_count": len(baseline_ids & current_ids),
    }


def listening_concentration(data: dict, top_n: int = 5) -> dict:
    primary_artists = [item["artists"][0]["name"] for item in data["items"]]

    total = len(primary_artists)
    counter = Counter(primary_artists)
    ranking = counter.most_common(top_n)

    top_3_count = sum(count for _, count in counter.most_common(3))

    return {
        "total_tracks": total,
        "distinct_artists": len(counter),
        "tracks_per_artist": round(total / len(counter), 2),
        "top_3_share": round(top_3_count / total * 100, 1),
        "top_artists": [
            {"name": name, "count": count, "share": round(count / total * 100, 1)}
            for name, count in ranking
        ],
    }
