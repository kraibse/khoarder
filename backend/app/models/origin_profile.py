from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OriginProfile(Base):
    """Per-domain memory: which strategy worked last, success/fail counts, cooldowns.

    Lets the orchestrator skip strategies known to fail for a host and start with
    the cheapest one that previously produced a good extraction.
    """

    __tablename__ = "origin_profiles"

    domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    last_strategy: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    last_challenge: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
