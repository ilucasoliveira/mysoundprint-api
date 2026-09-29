from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.services.spotify_auth import refresh_access_token

async def get_user_by_spotify_id(db: AsyncSession, spotify_account_id: str) -> User | None:
    result = await db.execute(select(User).where(User.spotify_account_id == spotify_account_id))
    return result.scalar_one_or_none()

async def upsert_user(db: AsyncSession, profile: dict, token_data: dict) -> User:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
    
    user = await get_user_by_spotify_id(db, profile["account_id"])
    if user is None:
        
        user = User(
            spotify_account_id=profile["account_id"],
            display_name=profile.get("display_name"),
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=expires_at
        )
        
        db.add(user)
    else:
        user.access_token = token_data["access_token"]
        user.refresh_token = token_data["refresh_token"]
        user.token_expires_at = expires_at
        
    await db.commit()
    await db.refresh(user)
    
    return user

async def get_valid_access_token(db: AsyncSession, user: User) -> str:
    if user.token_expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
        return user.access_token
    
    token_data = await refresh_access_token(user.refresh_token)
    
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
    
    user.access_token = token_data["access_token"]
    user.refresh_token = token_data.get("refresh_token") or user.refresh_token
    user.token_expires_at = expires_at
    
    await db.commit()
    await db.refresh(user)
    
    return user.access_token