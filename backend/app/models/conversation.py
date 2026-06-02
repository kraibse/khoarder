import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="New Conversation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    topic: Mapped["Topic"] = relationship("Topic", back_populates="conversations")  # type: ignore[name-defined]
    messages: Mapped[list["Message"]] = relationship(  # type: ignore[name-defined]
        "Message", back_populates="conversation", cascade="all, delete-orphan", lazy="select"
    )
