import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.tag import entry_tags


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # Article|Note|Paper|Excerpt|Reference
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    read_time_min: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    has_img: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    img_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    img_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    img_color: Mapped[str] = mapped_column(String(64), nullable=False, default="oklch(70% 0.05 200)")
    is_starred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    topic: Mapped["Topic"] = relationship("Topic", back_populates="entries")  # type: ignore[name-defined]
    tags: Mapped[list["Tag"]] = relationship(  # type: ignore[name-defined]
        "Tag", secondary=entry_tags, back_populates="entries", lazy="select"
    )
    attachments: Mapped[list["Attachment"]] = relationship(  # type: ignore[name-defined]
        "Attachment", back_populates="entry", cascade="all, delete-orphan", lazy="select"
    )
    relations_from: Mapped[list["Relation"]] = relationship(  # type: ignore[name-defined]
        "Relation", foreign_keys="Relation.from_entry_id", back_populates="from_entry", lazy="select"
    )
    relations_to: Mapped[list["Relation"]] = relationship(  # type: ignore[name-defined]
        "Relation", foreign_keys="Relation.to_entry_id", back_populates="to_entry", lazy="select"
    )
