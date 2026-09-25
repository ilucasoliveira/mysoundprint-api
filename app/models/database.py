from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import(
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from collections.abc import AsyncGenerator

from app.config import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.database_url)

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session