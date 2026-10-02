"""Google Fact Check fetcher: existing professional verdicts (P07 T07.015).

Claim Search API; one doc per claimReview (publisher, rating, review URL).
Lookup-only: reviews live on publisher sites, which the web fetcher reads.
Disabled without GOOGLE_FACTCHECK_KEY.
"""

from __future__ import annotations

import logging

import httpx

from sots.models.evidence import FetchedDoc
from sots.research.fetchers.base import FetcherDeps, clean_text, doc_hash, fetch_json
from sots.research.fetchers.cache import write_cached

logger = logging.getLogger(__name__)

API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
#: Claim reviews kept per lookup (candidates cap the rest).
TOP_K = 5


class GoogleFactcheckFetcher:
    """The Google Fact Check backend (06 §3.2)."""

    name = "google_factcheck"

    def __init__(self, deps: FetcherDeps, api_key: str | None) -> None:
        self._deps = deps
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        """The Claim Search API needs a (free) key."""
        return bool(self.api_key)

    @property
    def disabled_reason(self) -> str:
        """Why this fetcher is unavailable (registry status use)."""
        return "missing GOOGLE_FACTCHECK_KEY"

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Claim reviews as publisher/rating docs (06 §3.2)."""
        if not self.enabled:
            return []
        try:
            payload = await fetch_json(
                API_URL, deps=self._deps,
                params={"query": query, "key": self.api_key},
            )
        except httpx.HTTPError as exc:
            logger.info("google_factcheck lookup %r failed: %s", query, exc)
            return []
        docs: list[FetchedDoc] = []
        for claim in payload.get("claims", []) or []:
            for review in claim.get("claimReview", []) or []:
                doc = self._review_doc(claim, review)
                if doc is not None:
                    write_cached(self._deps.cache_dir, doc)
                    docs.append(doc)
                if len(docs) >= TOP_K:
                    return docs
        return docs

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """Reviews live on publisher sites; the web fetcher reads them."""
        return None

    def _review_doc(
        self, claim: dict[str, object], review: dict[str, object]
    ) -> FetchedDoc | None:
        url = str(review.get("url", "") or "")
        if not url:
            return None
        publisher = review.get("publisher") or {}
        lines = [
            f"Claim: {claim.get('text', '?')}",
            f"Claimant: {claim.get('claimant', '?')}",
            f"Publisher: {publisher.get('name', '?')} ({publisher.get('site', '?')})",
            f"Rating: {review.get('textualRating', '?')}",
            f"Reviewed: {review.get('reviewDate', '?')}",
            f"Title: {review.get('title', '?')}",
        ]
        text = clean_text(
            "\n".join(lines), self._deps.settings.agents.injection_patterns
        )
        return FetchedDoc(
            url=url, title=str(review.get("title", "")), publisher=str(
                publisher.get("name", "") or None),
            published_date=None, text=text, content_hash=doc_hash(text),
            fetcher="google_factcheck",
        )
