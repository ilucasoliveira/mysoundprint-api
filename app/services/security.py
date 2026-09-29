import jwt

from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends
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
        raise CREDENTIALS_EXCEPTION
    except jwt.exceptions.InvalidTokenError:
        raise CREDENTIALS_EXCEPTION
    
    user_id = int(decoded_token["sub"])
    return user_id

async def get_current_user(auth: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)), db: AsyncSession = Depends(get_db)) -> User:
    if auth is None:
        raise CREDENTIALS_EXCEPTION
    
    user_id = decode_access_token(auth.credentials)
    user = await db.get(User, user_id)
    if not user:
        raise CREDENTIALS_EXCEPTION
    
    return user
