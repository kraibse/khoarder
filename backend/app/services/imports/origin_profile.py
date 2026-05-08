"""Per-origin success memory, persisted in the `origin_profiles` table.

The orchestrator asks for a hint before fetching. If the previous import
for this domain succeeded with a specific strategy, the orchestrator starts
there instead of paying for `static_http` first. Repeated failures put the
domain into a short cooldown so static fetches stop hitting it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.origin_profile import OriginProfile
from app.services.imports.types import ChallengeType

logger = logging.getLogger(__name__)

# Number of consecutive failures before a static fetch is skipped for the domain.
STATIC_COOLDOWN_THRESHOLD = 3
STATIC_COOLDOWN_DURATION = timedelta(hours=1)


def domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


async def get_profile(db: AsyncSession, domain: str) -> OriginProfile | None:
    if not domain:
        return None
    result = await db.execute(select(OriginProfile).where(OriginProfile.domain == domain))
    return result.scalar_one_or_none()


async def hint_for(db: AsyncSession, url: str) -> tuple[str | None, bool]:
    """Return (preferred_strategy, skip_static).

    `preferred_strategy` is the one that worked last time, or None.
    `skip_static` is True when a recent run of failures puts the domain on
    static-fetch cooldown — saves wall time on known-blocked domains.
    """
    profile = await get_profile(db, domain_of(url))
    if profile is None:
        return None, False
    skip_static = False
    if profile.cooldown_until is not None:
        cooldown = profile.cooldown_until
        if cooldown.tzinfo is None:
            cooldown = cooldown.replace(tzinfo=timezone.utc)
        if cooldown > datetime.now(timezone.utc):
            skip_static = True
    return (profile.last_strategy or None), skip_static


async def record_success(db: AsyncSession, url: str, strategy: str) -> None:
    domain = domain_of(url)
    if not domain:
        return
    profile = await get_profile(db, domain)
    now = datetime.now(timezone.utc)
    if profile is None:
        profile = OriginProfile(
            domain=domain,
            last_strategy=strategy,
            last_challenge=ChallengeType.NONE.value,
            success_count=1,
            fail_count=0,
            last_success_at=now,
            cooldown_until=None,
        )
        db.add(profile)
    else:
        profile.last_strategy = strategy
        profile.last_challenge = ChallengeType.NONE.value
        profile.success_count += 1
        profile.fail_count = 0
        profile.last_success_at = now
        profile.cooldown_until = None
    try:
        await db.commit()
    except Exception as exc:
        logger.debug("origin profile commit (success) failed: %s", exc)
        await db.rollback()


async def record_failure(db: AsyncSession, url: str, challenge: ChallengeType, last_strategy: str) -> None:
    domain = domain_of(url)
    if not domain:
        return
    profile = await get_profile(db, domain)
    now = datetime.now(timezone.utc)
    if profile is None:
        profile = OriginProfile(
            domain=domain,
            last_strategy=last_strategy,
            last_challenge=challenge.value,
            success_count=0,
            fail_count=1,
            last_success_at=None,
            cooldown_until=None,
        )
        db.add(profile)
    else:
        profile.last_challenge = challenge.value
        profile.fail_count += 1
        if profile.fail_count >= STATIC_COOLDOWN_THRESHOLD:
            profile.cooldown_until = now + STATIC_COOLDOWN_DURATION
    try:
        await db.commit()
    except Exception as exc:
        logger.debug("origin profile commit (failure) failed: %s", exc)
        await db.rollback()
