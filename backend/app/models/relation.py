import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Relation(Base):
    __tablename__ = "relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    from_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    to_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # backlink | related

    from_entry: Mapped["Entry"] = relationship(  # type: ignore[name-defined]
        "Entry", foreign_keys=[from_entry_id], back_populates="relations_from"
    )
    to_entry: Mapped["Entry"] = relationship(  # type: ignore[name-defined]
        "Entry", foreign_keys=[to_entry_id], back_populates="relations_to"
    )
