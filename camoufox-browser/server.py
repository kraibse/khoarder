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


async def handle_fetch(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"status": "error", "message": "invalid JSON"}, status=400)

    url = (body.get("url") or "").strip()
    timeout_s = int(body.get("timeout", 30))

    if not url:
        return web.json_response({"status": "error", "message": "url is required"}, status=400)

    logger.info("fetch %s (timeout=%ss)", url, timeout_s)

    async with _sem:
        try:
            async with AsyncCamoufox(headless=True) as browser:
                page = await browser.new_page()
                try:
                    await page.goto(url, timeout=timeout_s * 1000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=timeout_s * 1000)
                    except Exception:
                        pass  # networkidle timeout is common; still return what we have
                    html = await page.content()
                finally:
                    await page.close()

            logger.info("fetch ok %s (%d bytes)", url, len(html))
            return web.json_response({"status": "ok", "html": html})

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
