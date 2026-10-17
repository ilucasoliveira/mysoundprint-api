from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class ListeningHistory(Base):
    """One row per play, accumulated over time.

    The Spotify recently-played endpoint only ever returns the last 50 plays
    and cannot be paginated into the past, so any long term listening history
    has to be collected and stored by this application.
    """

    __tablename__ = "listening_history"
    __table_args__ = (
        UniqueConstraint("user_id", "played_at", name="uq_history_user_played_at"),
        Index("ix_history_user_played_at", "user_id", "played_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    track_id: Mapped[str] = mapped_column(String(64), nullable=False)
    track_name: Mapped[str] = mapped_column(String(512), nullable=False)
    artist_name: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
