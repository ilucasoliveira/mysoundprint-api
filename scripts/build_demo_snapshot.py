"""Regenerate the demo snapshots from a live Spotify account.

Run it once, after logging in at least one time through /auth/login:

    poetry run python -m scripts.build_demo_snapshot --user-id 1

Note the -m: running the file by path puts `scripts/` on sys.path instead of
the project root, and `app` is then not importable.

Everything written here ends up in a public repository, so it only stores
top items and recently played tracks. No tokens, no profile, no email.
"""

import argparse
import asyncio
import json
from pathlib import Path

from app.models.database import SessionLocal
from app.models.user import User
from app.services.spotify_client import get_top_items, spotify_get
from app.services.user_service import get_valid_access_token
from scripts._slim import slim_payload

DEMO_DIR = Path(__file__).resolve().parent.parent / "app" / "demo_data"
TIME_RANGES = ("short_term", "medium_term", "long_term")
ITEM_TYPES = ("artists", "tracks")


def write(name: str, payload: dict, kind: str) -> None:
    """Store only the fields the statistics read, which is about a third of
    what Spotify sends and stays out of the repository forever otherwise."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    slim = slim_payload(payload, kind)
    target = DEMO_DIR / f"{name}.json"
    target.write_text(
        json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {target.name} ({len(slim.get('items', []))} items)")


async def build(user_id: int) -> None:
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None:
            raise SystemExit(
                f"user {user_id} not found, log in through /auth/login first"
            )

        for item_type in ITEM_TYPES:
            for time_range in TIME_RANGES:
                payload = await get_top_items(db, user, item_type, time_range, 50)
                write(f"top_{item_type}_{time_range}", payload, item_type)

        token = await get_valid_access_token(db, user)
        recent = await spotify_get(token, "/me/player/recently-played", {"limit": 50})
        write("recently_played", recent, "recently_played")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(build(args.user_id))


if __name__ == "__main__":
    main()
