import base64
import httpx

from app.config import settings

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

def _build_basic_auth_header() -> str:
    spotify_client_data = f"{settings.spotify_client_id}:{settings.spotify_client_secret.get_secret_value()}"
    
    credentials_bytes = spotify_client_data.encode()
    encoded = base64.b64encode(credentials_bytes)
    header_value = encoded.decode()
    
    return "Basic " + header_value

async def exchange_code_for_token(code: str) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.spotify_redirect_uri
    }
    
    headers = {"Authorization": _build_basic_auth_header()}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
        response.raise_for_status()
        return response.json()