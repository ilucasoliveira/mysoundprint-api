from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db
from app.models.user import User

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=401,
    detail="invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
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
    # `from None` on purpose. An expired token and a forged one are different
    # facts, and the caller is told neither: the same opaque 401 goes back
    # either way, with no chained traceback hinting at which it was.
    except jwt.exceptions.ExpiredSignatureError:
        raise CREDENTIALS_EXCEPTION from None
    except jwt.exceptions.InvalidTokenError:
        raise CREDENTIALS_EXCEPTION from None
    
    user_id = int(decoded_token["sub"])
    return user_id

async def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User:
    if auth is None:
        raise CREDENTIALS_EXCEPTION
    
    user_id = decode_access_token(auth.credentials)
    user = await db.get(User, user_id)
    if not user:
        raise CREDENTIALS_EXCEPTION
    
    return user
