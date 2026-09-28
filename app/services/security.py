import jwt

from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from app.config import settings

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "exp": exp,
        "iat": now
    }
    secret_key = settings.jwt_secret_key.get_secret_value()
    return jwt.encode(payload, secret_key, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> int:
    try:
        secret_key = settings.jwt_secret_key.get_secret_value()
        decoded_token = jwt.decode(token, secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="unauthorized credentials")
    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(status_code=401, detail="unauthorized credentials")
    
    user_id = int(decoded_token["sub"])
    return user_id
