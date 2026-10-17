"""Shrink Spotify payloads down to the fields the statistics actually read.

The raw responses carry three image sizes, market lists and several URL
variants per item. None of that is used here, and all of it would sit in a
public repository forever.
"""


def _smallest_image(images: list | None) -> list:
    if not images:
        return []
    smallest = min(images, key=lambda image: image.get("width") or 0)
    return [{"url": smallest.get("url"), "width": smallest.get("width")}]


def slim_artist(artist: dict) -> dict:
    return {
        "id": artist.get("id"),
        "name": artist.get("name"),
    }


def slim_album(album: dict) -> dict:
    return {
        "id": album.get("id"),
        "name": album.get("name"),
        "release_date": album.get("release_date"),
        "release_date_precision": album.get("release_date_precision"),
        "images": _smallest_image(album.get("images")),
    }


def slim_track(track: dict) -> dict:
    return {
        "id": track.get("id"),
        "name": track.get("name"),
        "duration_ms": track.get("duration_ms"),
        "explicit": track.get("explicit"),
        "artists": [slim_artist(artist) for artist in track.get("artists", [])],
        "album": slim_album(track.get("album", {})),
        "external_urls": {"spotify": (track.get("external_urls") or {}).get("spotify")},
    }


def slim_top_artist(artist: dict) -> dict:
    return {
        "id": artist.get("id"),
        "name": artist.get("name"),
        "images": _smallest_image(artist.get("images")),
        "external_urls": {"spotify": (artist.get("external_urls") or {}).get("spotify")},
    }


def slim_payload(payload: dict, item_type: str) -> dict:
    """item_type is "artists", "tracks" or "recently_played"."""
    items = payload.get("items", [])

    if item_type == "artists":
        slim_items = [slim_top_artist(item) for item in items]
    elif item_type == "tracks":
        slim_items = [slim_track(item) for item in items]
    else:
        slim_items = [
            {
                "played_at": item.get("played_at"),
                "track": slim_track(item.get("track") or item.get("item") or {}),
            }
            for item in items
        ]

    slim = {"items": slim_items, "limit": len(slim_items)}
    if "total" in payload:
        slim["total"] = payload["total"]
    return slim
