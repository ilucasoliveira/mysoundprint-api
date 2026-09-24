from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

from app.config import settings

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SCOPES = "user-top-read user-read-recently-played"

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login")
def spotify_login():
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": SCOPES
    }
    url = f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"
    
    return RedirectResponse(url)