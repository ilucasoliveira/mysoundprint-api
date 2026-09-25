import secrets

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

from app.config import settings
from app.services.redis_client import redis_client
from app.services.spotify_auth import exchange_code_for_token

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

@router.get("/callback")
async def spotify_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(status_code=400, detail=f"authorization failed: {error}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing code or state")
    
    saved_state = await redis_client.getdel(_state_key(state))
    if saved_state is None:
        raise HTTPException(status_code=400, detail="invalid or expired state")
    
    token_data = await exchange_code_for_token(code)
    
    return {"ok": True, "expires_in": token_data["expires_in"], "scope": token_data["scope"]}