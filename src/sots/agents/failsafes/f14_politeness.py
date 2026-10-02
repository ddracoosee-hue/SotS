"""F14 politeness: per-domain rate limits + robots.txt (P03 T03.053, 16 §5.1).

One token bucket per domain (default 1 req/s from
`settings.fetch.per_domain_rate_limit_per_s`), a robots.txt cache, and a
User-Agent identifying the project with CONTACT_EMAIL. The clock and sleeper
are injectable for deterministic tests.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

RobotsFetch = Callable[[str], Awaitable[str | None]]


class TokenBucket:
    """Token bucket; `acquire` sleeps until a token is available."""

    def __init__(
        self,
        rate_per_s: float,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if rate_per_s <= 0:
            raise ValueError("rate_per_s must be positive")
        self._rate = rate_per_s
        self._time = time_fn
        self._sleep = sleep_fn
        self._allowance = rate_per_s
        self._last = time_fn()

    async def acquire(self) -> None:
        now = self._time()
        elapsed = now - self._last
        self._last = now
        self._allowance = min(self._rate, self._allowance + elapsed * self._rate)
        if self._allowance >= 1.0:
            self._allowance -= 1.0
            return
        wait = (1.0 - self._allowance) / self._rate
        await self._sleep(wait)
        self._last = self._time()
        self._allowance = 0.0


def parse_robots(robots_txt: str) -> list[str]:
    """Disallow prefixes applying to `User-agent: *` (minimal parser)."""
    disallows: list[str] = []
    applies = False
    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            applies = value == "*"
        elif field == "disallow" and applies and value:
            disallows.append(value)
    return disallows


def robots_allows(disallows: list[str], path: str) -> bool:
    """True unless a Disallow prefix matches the path."""
    return not any(path.startswith(prefix) for prefix in disallows)


class PolitenessGate:
    """Rate limiting + robots.txt cache shared by fetchers (F14)."""

    def __init__(
        self,
        rate_per_s: float,
        contact_email: str,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._rate = rate_per_s
        self._contact = contact_email
        self._time_fn = time_fn
        self._sleep_fn = sleep_fn
        self._buckets: dict[str, TokenBucket] = {}
        self._robots: dict[str, list[str] | None] = {}

    @property
    def user_agent(self) -> str:
        """Identifying User-Agent (CONTACT_EMAIL when set)."""
        if self._contact:
            return f"SotS research fetcher (+{self._contact})"
        return "SotS research fetcher (contact unknown)"

    def _bucket(self, domain: str) -> TokenBucket:
        bucket = self._buckets.get(domain)
        if bucket is None:
            bucket = TokenBucket(self._rate, self._time_fn, self._sleep_fn)
            self._buckets[domain] = bucket
        return bucket

    async def acquire(self, url: str) -> None:
        """Wait until `url`'s domain bucket has a token."""
        await self._bucket(urlparse(url).netloc.lower()).acquire()

    async def robots_allowed(self, url: str, fetch: RobotsFetch) -> bool:
        """robots.txt verdict for `url` (fetched once per domain, then cached)."""
        parts = urlparse(url)
        domain = parts.netloc.lower()
        if domain not in self._robots:
            text = await fetch(f"{parts.scheme}://{parts.netloc}/robots.txt")
            self._robots[domain] = parse_robots(text) if text is not None else []
        cached = self._robots[domain]
        return robots_allows(cached or [], parts.path or "/")
