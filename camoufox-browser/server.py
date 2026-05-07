import asyncio
import logging
import os

from aiohttp import web
from camoufox.async_api import AsyncCamoufox

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", 3392))

# Semaphore limits concurrent browser instances so the container doesn't OOM
# under accidental parallel requests. One at a time is fine for a fallback service.
_sem = asyncio.Semaphore(1)

# Markers that signal a bot/anti-automation interstitial is still showing.
# Kept in sync (loosely) with backend/app/services/entries.py:_is_bot_challenge.
_CHALLENGE_MARKERS = (
    "just a moment",
    "attention required",
    "performing security verification",
    "security verification",
    "security check",
    "checking your browser",
    "ddos protection",
    "bot detection",
    "captcha",
    "please wait while we verify",
    "please wait",
    "verify you are human",
    "verify you're human",
    "human verification",
    "ray id",
    "cf-chl",
    "cf_chl",
    "challenge-platform",
)


def _is_challenge(html: str) -> bool:
    if not html:
        return True
    lower = html.lower()
    return any(m in lower for m in _CHALLENGE_MARKERS)


async def _wait_for_real_content(page, deadline: float) -> str:
    """Poll page content until the bot-challenge markers disappear or deadline expires.

    Cloudflare-style interstitials self-resolve after a few seconds of JS execution.
    page.goto returns when the *interstitial* fires its load event, so we have to
    keep waiting after that to capture the real content.
    """
    html = await page.content()
    if not _is_challenge(html):
        return html

    while asyncio.get_event_loop().time() < deadline:
        # Small bursts: networkidle for in-flight challenge XHRs, then sleep, then re-read.
        try:
            await page.wait_for_load_state("networkidle", timeout=4_000)
        except Exception:
            pass
        await asyncio.sleep(1.5)
        html = await page.content()
        if not _is_challenge(html):
            return html

    return html


async def handle_fetch(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"status": "error", "message": "invalid JSON"}, status=400)

    url = (body.get("url") or "").strip()
    timeout_s = int(body.get("timeout", 60))

    if not url:
        return web.json_response({"status": "error", "message": "url is required"}, status=400)

    logger.info("fetch %s (timeout=%ss)", url, timeout_s)

    async with _sem:
        try:
            deadline = asyncio.get_event_loop().time() + timeout_s
            async with AsyncCamoufox(headless=True) as browser:
                page = await browser.new_page()
                try:
                    # domcontentloaded is the lightest event that guarantees we have a DOM.
                    # We then poll content until any bot challenge clears.
                    await page.goto(url, timeout=timeout_s * 1000, wait_until="domcontentloaded")

                    # Best-effort: wait for the network to settle once before sampling.
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10_000)
                    except Exception:
                        pass

                    html = await _wait_for_real_content(page, deadline)

                    # SPAs (e.g. semanticscholar.org) ship a tiny shell and hydrate via JS.
                    # If the doc still looks empty after the challenge cleared, give the
                    # frontend bundle one more beat before sampling.
                    if len(html) < 8000 and asyncio.get_event_loop().time() < deadline:
                        await asyncio.sleep(2.0)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=4_000)
                        except Exception:
                            pass
                        html = await page.content()

                    final_url = page.url
                finally:
                    await page.close()

            challenge = _is_challenge(html)
            logger.info(
                "fetch ok %s (%d bytes, final=%s, challenge=%s)",
                url, len(html), final_url, challenge,
            )
            return web.json_response({
                "status": "ok",
                "html": html,
                "final_url": final_url,
                "challenge": challenge,
            })

        except Exception as exc:
            logger.error("fetch failed %s: %s", url, exc)
            return web.json_response({"status": "error", "message": str(exc)}, status=500)


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "camoufox-browser"})


app = web.Application()
app.router.add_get("/health", handle_health)
app.router.add_post("/fetch", handle_fetch)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
