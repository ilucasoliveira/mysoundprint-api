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


def _build_detail_map(data: dict) -> dict[str, dict]:
    """Image and Spotify link per item, for whichever side has them."""
    details = {}
    for item in data["items"]:
        images = item.get("images") or (item.get("album") or {}).get("images") or []
        details[item["id"]] = {
            "image": images[0].get("url") if images else None,
            "spotify_url": (item.get("external_urls") or {}).get("spotify"),
        }
    return details


def compare_time_ranges(baseline: dict, current: dict) -> dict:
    baseline_positions = _build_position_map(baseline)
    current_positions = _build_position_map(current)
    names = _build_name_map(baseline) | _build_name_map(current)
    details = _build_detail_map(baseline) | _build_detail_map(current)

    baseline_ids = set(baseline_positions)
    current_ids = set(current_positions)

    entered = [
        {
            "id": item_id,
            "name": names[item_id],
            "position": current_positions[item_id],
            **details.get(item_id, {}),
        }
        for item_id in sorted(current_ids - baseline_ids, key=current_positions.get)
    ]

    dropped = [
        {
            "id": item_id,
            "name": names[item_id],
            "position": baseline_positions[item_id],
            **details.get(item_id, {}),
        }
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
            **details.get(item_id, {}),
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


def _artwork(item: dict) -> str | None:
    """Smallest album cover Spotify sent for this track.

    Spotify's guidelines require its artwork to be used as provided, so the
    URL is passed through untouched and never re-hosted or edited."""
    images = (item.get("album") or {}).get("images") or []
    return images[0].get("url") if images else None


def listening_concentration(data: dict, top_n: int = 5) -> dict:
    items = data["items"]
    primary_artists = [item["artists"][0]["name"] for item in items]

    total = len(primary_artists)
    counter = Counter(primary_artists)
    ranking = counter.most_common(top_n)

    top_3_count = sum(count for _, count in counter.most_common(3))

    # One representative track per artist, so the ranking can show cover art
    # without a second request to Spotify.
    sample: dict[str, dict] = {}
    for item in items:
        name = item["artists"][0]["name"]
        sample.setdefault(name, item)

    return {
        "total_tracks": total,
        "distinct_artists": len(counter),
        "tracks_per_artist": round(total / len(counter), 2),
        "top_3_share": round(top_3_count / total * 100, 1),
        "top_artists": [
            {
                "name": name,
                "count": count,
                "share": round(count / total * 100, 1),
                "image": _artwork(sample.get(name, {})),
                "track_name": sample.get(name, {}).get("name"),
                "spotify_url": (sample.get(name, {}).get("external_urls") or {}).get(
                    "spotify"
                ),
            }
            for name, count in ranking
        ],
    }
