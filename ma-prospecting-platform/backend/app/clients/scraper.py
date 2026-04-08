import logging
from dataclasses import dataclass, field
from typing import Literal

import httpx
from bs4 import BeautifulSoup

from app.utils.scrape_quality import is_usable_text, text_quality_score

logger = logging.getLogger(__name__)

ScrapeTier = Literal["high", "degraded_curl", "low"]


@dataclass
class ScrapeResult:
    """Result of direct HTTP scraping before web-search or Playwright fallback in target_profiler."""

    text: str
    tier: ScrapeTier
    methods: tuple[str, ...] = field(default_factory=tuple)


# Full browser-like headers — incomplete User-Agents are often blocked with 403.
DEFAULT_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


async def _fetch_html_curl_cffi(url: str, timeout: int) -> str:
    """Cloudflare and similar CDNs often block plain httpx; curl_cffi mimics browser TLS."""
    try:
        from curl_cffi.requests import AsyncSession
    except ImportError as e:
        raise RuntimeError(
            "Site returned 403 (likely bot protection). Install dependency: pip install curl-cffi"
        ) from e

    async with AsyncSession() as session:
        resp = await session.get(
            url,
            impersonate="chrome",
            timeout=timeout,
            verify=False,
        )
        resp.raise_for_status()
        return resp.text


async def _fetch_html_httpx(url: str, timeout: int) -> tuple[str, bool]:
    """
    Returns (html, used_curl_fallback).
    On 403, retries with Referer then curl_cffi.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, verify=False) as client:
        response = await client.get(url, headers=DEFAULT_BROWSER_HEADERS)
        if response.status_code == 403:
            logger.warning("Got 403 — retrying with Referer fallback for %s", url)
            response = await client.get(
                url,
                headers={
                    **DEFAULT_BROWSER_HEADERS,
                    "Referer": "https://www.google.com/",
                    "Sec-Fetch-Site": "cross-site",
                },
            )
        if response.status_code == 403:
            logger.warning(
                "403 with httpx (often Cloudflare); using curl_cffi browser impersonation for %s",
                url,
            )
            html = await _fetch_html_curl_cffi(url, timeout)
            return html, True
        response.raise_for_status()
        ct = response.headers.get("content-type", "")
        logger.debug("Fetched %s content-type=%s len=%s", url, ct, len(response.text))
        return response.text, False


async def fetch_html_best_effort(url: str, timeout: int) -> tuple[str, tuple[str, ...]]:
    """
    Try httpx first; if extracted text is low quality, retry full fetch with curl_cffi
    (SPA / bot sites often return 200 with empty shells to httpx).
    """
    html_httpx, curl_from_403 = await _fetch_html_httpx(url, timeout)
    text_h = _html_to_text(html_httpx, url, log_len=False)
    methods: list[str] = ["httpx"] if not curl_from_403 else ["httpx", "curl_cffi_403"]

    if curl_from_403:
        logger.info(
            "Scrape %s: used curl after 403, quality_usable=%s chars=%s",
            url,
            is_usable_text(text_h),
            len(text_h),
        )
        return html_httpx, tuple(methods)

    if is_usable_text(text_h):
        logger.info("Scrape %s: httpx OK, chars=%s", url, len(text_h))
        return html_httpx, tuple(methods)

    logger.warning(
        "Low-quality text after httpx for %s (chars=%s) — retrying fetch with curl_cffi",
        url,
        len(text_h),
    )
    try:
        html_curl = await _fetch_html_curl_cffi(url, timeout)
        text_c = _html_to_text(html_curl, url, log_len=False)
        methods.append("curl_cffi_quality")
        if text_quality_score(text_c) > text_quality_score(text_h) or is_usable_text(text_c):
            logger.info(
                "curl_cffi improved scrape for %s: chars=%s usable=%s",
                url,
                len(text_c),
                is_usable_text(text_c),
            )
            return html_curl, tuple(methods)
    except Exception as e:
        logger.warning("curl_cffi quality retry failed for %s: %s", url, e)

    return html_httpx, tuple(methods)


def _html_to_text(html: str, url: str, *, log_len: bool = True) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
        tag.decompose()

    for tag in soup.find_all(attrs={"style": lambda s: s and "display:none" in s.replace(" ", "")}):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = "\n".join(lines)

    max_chars = 50000
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n\n[Content truncated]"

    if log_len:
        logger.info("Scraped %s: %s characters", url, len(cleaned))
    return cleaned


async def scrape_url(url: str, timeout: int = 30) -> str:
    """Scrape a URL and return cleaned text (backward-compatible single string)."""
    result = await scrape_url_detailed(url, timeout=timeout)
    return result.text


async def scrape_url_detailed(url: str, timeout: int = 30) -> ScrapeResult:
    """Scrape with quality-aware curl retry; sets tier high / degraded_curl / low."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    html, methods = await fetch_html_best_effort(url, timeout)
    text = _html_to_text(html, url)
    if is_usable_text(text):
        tier: ScrapeTier = "degraded_curl" if any("curl_cffi" in m for m in methods) else "high"
    else:
        tier = "low"
    return ScrapeResult(text=text, tier=tier, methods=tuple(methods))


async def fetch_rendered_text_playwright(url: str, timeout: int = 45) -> str:
    """
    Render page in Chromium (JS SPAs). Requires: pip install playwright && playwright install chromium
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise RuntimeError(
            "Playwright not installed. Use: pip install playwright && playwright install chromium"
        ) from e

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            await page.wait_for_timeout(2000)
            body = await page.inner_text("body")
        finally:
            await browser.close()

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    cleaned = "\n".join(lines)
    if len(cleaned) > 50000:
        cleaned = cleaned[:50000] + "\n\n[Content truncated]"
    logger.info("Playwright rendered %s: %s characters", url, len(cleaned))
    return cleaned
