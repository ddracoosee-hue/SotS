"""Supplements fetcher: the author's own reference files (P07 T07.019).

BM25-lite over the indexed `supplements/` texts; hits come back as
FetchedDocs under `supplements://` URLs (evidence built from them carries
source_class AUTHOR_SUPPLEMENT). Local files also land in the fetch cache so
citation checks treat every source alike.
"""

from __future__ import annotations

from sots.models.evidence import FetchedDoc
from sots.research.bm25 import score_texts
from sots.research.fetchers.base import FetcherDeps, doc_hash
from sots.research.fetchers.cache import write_cached
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

#: Supplements kept per lookup (candidates cap the rest).
TOP_K = 5
SCHEME = "supplements://"


class SupplementsFetcher:
    """The local-supplements backend (06 §3.2)."""

    name = "supplements"

    def __init__(self, deps: FetcherDeps, conn: Connection) -> None:
        self._deps = deps
        self._conn = conn

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Top indexed supplements by BM25-lite score (06 §3.2)."""
        docs = storage_repo.list_supplement_docs(self._conn)
        if not docs:
            return []
        scores = score_texts([doc.text for doc in docs], query)
        ranked = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
        out: list[FetchedDoc] = []
        for index in ranked[:TOP_K]:
            if scores[index] <= 0:
                continue
            fetched = _as_fetched(docs[index].path, docs[index].text)
            write_cached(self._deps.cache_dir, fetched)
            out.append(fetched)
        return out

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """One indexed file by its `supplements://` URL."""
        if not url.startswith(SCHEME):
            return None
        doc = storage_repo.get_supplement_doc(self._conn, url[len(SCHEME):])
        if doc is None:
            return None
        fetched = _as_fetched(doc.path, doc.text)
        write_cached(self._deps.cache_dir, fetched)
        return fetched


def _as_fetched(path: str, text: str) -> FetchedDoc:
    return FetchedDoc(
        url=f"{SCHEME}{path}", title=path, publisher=None, published_date=None,
        text=text, content_hash=doc_hash(text), fetcher="supplements",
    )
