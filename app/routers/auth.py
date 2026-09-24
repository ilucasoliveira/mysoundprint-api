import secrets

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

from app.config import settings
from app.services.redis_client import redis_client

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SCOPES = "user-top-read user-read-recently-played"

router = APIRouter(prefix="/auth", tags=["auth"])

def _state_key(state: str) -> str:
    return f"oauth_state:{state}"

@router.get("/login")
async def spotify_login():
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": SCOPES,
        "state": state
    }
    
    await redis_client.set(_state_key(state), "1", ex=300)
    
    url = f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)