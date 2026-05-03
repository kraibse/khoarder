import uuid

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

entry_tags = Table(
    "entry_tags",
    Base.metadata,
    Column("entry_id", String(36), ForeignKey("entries.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    entries: Mapped[list["Entry"]] = relationship(  # type: ignore[name-defined]
        "Entry", secondary=entry_tags, back_populates="tags", lazy="select"
    )
