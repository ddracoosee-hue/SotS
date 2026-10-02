"""`fetch_url`: minimal page/PDF fetcher (P03 T03.022, 16 §3).

Downloads with the F14 gate (rate limit + robots.txt + User-Agent), extracts
HTML text with trafilatura (stdlib fallback), and caches the full artifact by
content hash. Returns FetchedDoc metadata + a text preview; the full text
lives in the cache, not the observation. P07 replaces this with the full
research fetcher; the cache layout stays compatible.
"""

from __future__ import annotations

import hashlib
import json
import logging
from urllib.parse import urlparse

import httpx
import trafilatura
from pydantic import BaseModel, ConfigDict

from sots.agents.failsafes.f14_politeness import PolitenessGate
from sots.agents.tools.base import ToolContext, cache_path, register_tool
from sots.models.agents import Observation
from sots.models.evidence import FetchedDoc
from sots.storage.files import atomic_write_bytes, atomic_write_text, ensure_dir

logger = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024
PREVIEW_CHARS = 2000

_GATES: dict[tuple[float, str | None], PolitenessGate] = {}


def _gate_for(ctx: ToolContext) -> PolitenessGate:
    key = (ctx.settings.fetch.per_domain_rate_limit_per_s, ctx.settings.secrets.contact_email)
    gate = _GATES.get(key)
    if gate is None:
        gate = PolitenessGate(rate_per_s=key[0], contact_email=key[1] or "")
        _GATES[key] = gate
    return gate


def _content_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class FetchUrlArgs(BaseModel):
    """URL to fetch (http/https only)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str


class FetchUrlTool:
    """`fetch_url`: trafilatura + cache + politeness (16 §3)."""

    name = "fetch_url"
    internet = True
    args_model = FetchUrlArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, FetchUrlArgs)
        url = args.url.strip()
        if urlparse(url).scheme not in ("http", "https"):
            return Observation(
                tool=self.name, ok=False, content="error: only http/https URLs", truncated=False
            )
        gate = _gate_for(ctx)
        timeout = httpx.Timeout(ctx.settings.fetch.timeout_s)
        headers = {"User-Agent": gate.user_agent}
        try:
            await gate.acquire(url)
            async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
                if not await gate.robots_allowed(url, lambda u: _fetch_robots(client, u)):
                    return Observation(
                        tool=self.name, ok=False,
                        content="error: blocked by robots.txt", truncated=False,
                    )
                await gate.acquire(url)
                async with client.stream("GET", url, follow_redirects=True) as response:
                    response.raise_for_status()
                    raw_type = response.headers.get("content-type", "")
                    content_type = raw_type.split(";")[0].strip().lower()
                    domain = urlparse(str(response.url)).netloc.lower()
                    body = await _read_capped(response)
        except httpx.HTTPError as exc:
            return Observation(
                tool=self.name, ok=False,
                content=f"error: fetch failed ({type(exc).__name__}: {exc})", truncated=False,
            )
        if body is None:
            return Observation(
                tool=self.name, ok=False,
                content=f"error: response exceeds the {MAX_BYTES}-byte cap", truncated=False,
            )
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return self._store_pdf(ctx, url, domain, body)
        if "html" not in content_type and "text" not in content_type:
            return Observation(
                tool=self.name, ok=False,
                content=f"error: unsupported content-type {content_type!r}", truncated=False,
            )
        return self._store_html(ctx, url, domain, body)

    def _store_html(self, ctx: ToolContext, url: str, domain: str, body: bytes) -> Observation:
        html = body.decode("utf-8", errors="replace")
        text = trafilatura.extract(html) or ""
        if not text.strip():
            from sots.agents.tools.parse_html import parse_html

            text, _ = parse_html(html)
        digest = _content_hash(text.encode("utf-8"))
        doc = FetchedDoc(
            url=url, title="", publisher=domain or None, published_date=None,
            text=text, content_hash=digest, fetcher="fetch_url/p03",
        )
        cache_file = cache_path(ctx, "fetch", f"{digest}.json")
        ensure_dir(cache_file.parent)
        atomic_write_text(cache_file, doc.model_dump_json())
        logger.info("fetch_url cached %s (%d chars)", url, len(text))
        payload = {
            "url": url, "publisher": doc.publisher, "content_hash": digest,
            "chars": len(text), "text_preview": text[:PREVIEW_CHARS],
            "truncated": len(text) > PREVIEW_CHARS,
            "cache": str(cache_file),
        }
        return Observation(
            tool=self.name, ok=True, content=json.dumps(payload),
            truncated=len(text) > PREVIEW_CHARS,
        )

    def _store_pdf(self, ctx: ToolContext, url: str, domain: str, body: bytes) -> Observation:
        digest = _content_hash(body)
        cache_file = cache_path(ctx, "fetch", f"{digest}.pdf")
        ensure_dir(cache_file.parent)
        atomic_write_bytes(cache_file, body)
        payload = {
            "url": url, "publisher": domain or None, "content_hash": digest,
            "bytes": len(body), "cache": str(cache_file),
            "note": "PDF bytes cached; use parse_pdf on the cache path for text",
        }
        return Observation(tool=self.name, ok=True, content=json.dumps(payload), truncated=False)


async def _fetch_robots(client: httpx.AsyncClient, robots_url: str) -> str | None:
    """robots.txt text, or None on any failure (fail-open, logged)."""
    try:
        response = await client.get(robots_url, follow_redirects=True)
        if response.status_code != 200:
            return None
        return response.text
    except httpx.HTTPError as exc:
        logger.info("robots fetch failed for %s: %s", robots_url, exc)
        return None


async def _read_capped(response: httpx.Response) -> bytes | None:
    """Response body, or None when it exceeds MAX_BYTES."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_BYTES:
            return None
    return b"".join(chunks)


register_tool(FetchUrlTool())
