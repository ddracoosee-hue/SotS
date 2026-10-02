"""P07 web/wikipedia/supplements/registry tests (T07.010/011/019/020)."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import respx

from sots.agents.failsafes.f03_circuit import CircuitBreaker
from sots.agents.failsafes.f14_politeness import PolitenessGate
from sots.config import load_settings
from sots.models.document import SupplementDoc
from sots.research.fetchers.base import FetcherDeps, doc_hash
from sots.research.fetchers.cache import cache_paths
from sots.research.fetchers.registry import build_fetchers, fetcher_status
from sots.research.fetchers.supplements import SupplementsFetcher
from sots.research.fetchers.web import WebFetcher
from sots.research.fetchers.wikipedia import WikipediaFetcher
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

HTML_PAGE = """<html><head><title>Civic Decline</title></head><body><article>
<h1>Civic Decline</h1><p>First paragraph about civic life and its troubles.</p>
<p>Second paragraph with more detail on the same important topic.</p>
<p>Third paragraph concluding the argument with evidence and care.</p>
</article></body></html>"""


def _make_pdf(pages: list[str]) -> bytes:
    """Minimal valid multi-page PDF with a correct xref table."""
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{4 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for text in pages:
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET".encode()
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 3 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {len(objects) + 2} 0 R >>".encode()
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF".encode()
    )
    return bytes(out)


def _deps(cache_dir: Path, name: str) -> FetcherDeps:
    return FetcherDeps(
        settings=load_settings(CONFIG_DIR, env_file=None),
        cache_dir=cache_dir,
        gate=PolitenessGate(rate_per_s=100.0, contact_email="t@t.test"),
        breaker=CircuitBreaker(key=f"test:{name}"),
    )


def _robots() -> respx.Route:
    return respx.get("http://site.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow:\n")
    )


@respx.mock
async def test_web_html_caches(tmp_path: Path) -> None:
    """T07.010: HTML extracts, caches .txt + .json, and serves cache."""
    _robots()
    page = respx.get("http://site.test/article").mock(
        return_value=httpx.Response(
            200, text=HTML_PAGE, headers={"content-type": "text/html"})
    )
    fetcher = WebFetcher(_deps(tmp_path / "cache", "web"))
    doc = await fetcher.fetch_url("http://site.test/article")
    assert doc is not None
    assert doc.title == "Civic Decline"
    assert doc.publisher == "site.test"
    assert "civic life and its troubles" in doc.text
    assert doc.fetcher == "web"
    txt, meta = cache_paths(tmp_path / "cache", "http://site.test/article")
    assert txt.is_file() and meta.is_file()
    assert txt.read_text(encoding="utf-8") == doc.text
    again = await fetcher.fetch_url("http://site.test/article")
    assert again == doc
    assert page.call_count == 1  # the second hit served the cache


@respx.mock
async def test_web_pdf_404_nontext_oversized(tmp_path: Path) -> None:
    """T07.010: PDF extracts; 404/non-text/oversized fail closed to None."""
    _robots()
    respx.get("http://site.test/doc.pdf").mock(
        return_value=httpx.Response(
            200, content=_make_pdf(["Hello PDF text here."]),
            headers={"content-type": "application/pdf"})
    )
    respx.get("http://site.test/missing").mock(
        return_value=httpx.Response(404, text="nope"))
    respx.get("http://site.test/img.png").mock(
        return_value=httpx.Response(
            200, content=b"\x89PNG" + b"0" * 100,
            headers={"content-type": "image/png"})
    )
    respx.get("http://site.test/huge").mock(
        return_value=httpx.Response(
            200, content=b"x" * (6 * 1024 * 1024),
            headers={"content-type": "text/html"})
    )
    fetcher = WebFetcher(_deps(tmp_path / "cache", "web"))
    pdf = await fetcher.fetch_url("http://site.test/doc.pdf")
    assert pdf is not None and "Hello PDF text here." in pdf.text
    assert await fetcher.fetch_url("http://site.test/missing") is None
    assert await fetcher.fetch_url("http://site.test/img.png") is None
    assert await fetcher.fetch_url("http://site.test/huge") is None


@respx.mock
async def test_web_cache_ttl_refetches(tmp_path: Path) -> None:
    """Stale cache entries (past TTL) refetch from the network."""
    _robots()
    page = respx.get("http://site.test/article").mock(
        return_value=httpx.Response(
            200, text=HTML_PAGE, headers={"content-type": "text/html"})
    )
    cache = tmp_path / "cache"
    fetcher = WebFetcher(_deps(cache, "web"))
    first = await fetcher.fetch_url("http://site.test/article")
    assert first is not None and page.call_count == 1
    old = time.time() - 40 * 86400
    for path in cache_paths(cache, "http://site.test/article"):
        os.utime(path, (old, old))
    second = await fetcher.fetch_url("http://site.test/article")
    assert second == first
    assert page.call_count == 2


WIKI_HTML = """<html><body>
<h2><span class="mw-headline" id="Plot">Plot</span></h2>
<p>The hero journeys far and returns changed by trials.</p>
<h2><span class="mw-headline" id="Reception">Reception</span></h2>
<p>Critics praised the film widely across the globe.</p>
<ol class="references"><li><a href="https://critic.test/review-1">Review</a></li>
<li><a href="https://en.wikipedia.org/wiki/Other">Internal</a></li></ol>
</body></html>"""


@respx.mock
async def test_wikipedia_lookup_fetch_section_refs(tmp_path: Path) -> None:
    """T07.011: title search, full article, #Plot, leads, unknown heading."""
    respx.get("https://en.wikipedia.org/w/api.php").mock(
        return_value=httpx.Response(200, json={"query": {"search": [
            {"title": "Test Film"}, {"title": "Other Page"},
        ]}})
    )
    respx.get("https://en.wikipedia.org/api/rest_v1/page/html/Test_Film").mock(
        return_value=httpx.Response(200, text=WIKI_HTML))
    respx.get("https://en.wikipedia.org/api/rest_v1/page/html/Other_Page").mock(
        return_value=httpx.Response(404, text="gone"))
    fetcher = WikipediaFetcher(_deps(tmp_path / "cache", "wikipedia"))
    found = await fetcher.lookup("test film")
    assert [d.title for d in found] == ["Test Film"]
    full = await fetcher.fetch_url("https://en.wikipedia.org/wiki/Test_Film")
    assert full is not None
    assert "Returns changed by trials" in full.text or "returns changed" in full.text
    assert "https://critic.test/review-1" in full.text  # the lead
    assert "en.wikipedia.org/wiki/Other" not in full.text  # internal skipped
    plot = await fetcher.fetch_url("https://en.wikipedia.org/wiki/Test_Film#Plot")
    assert plot is not None and "returns changed" in plot.text
    assert "Critics praised" not in plot.text
    assert await fetcher.fetch_url(
        "https://en.wikipedia.org/wiki/Test_Film#Missing") is None
    assert await fetcher.fetch_url("https://example.com/wiki/Nope") is None


async def test_supplements_lookup_and_fetch(tmp_path: Path) -> None:
    """T07.019: BM25-lite ranks the author's files; URLs round-trip."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        now = datetime.now(UTC)
        storage_repo.save_supplement_doc(conn, SupplementDoc(
            path="notes.md", sha256="a" * 64,
            text="Divorce statistics and census methodology notes here.",
            indexed_at=now,
        ))
        storage_repo.save_supplement_doc(conn, SupplementDoc(
            path="other.md", sha256="b" * 64, text="Unrelated cooking trivia.",
            indexed_at=now,
        ))
        fetcher = SupplementsFetcher(
            _deps(tmp_path / "cache", "supplements"), conn)
        found = await fetcher.lookup("divorce statistics census")
        assert [d.url for d in found] == ["supplements://notes.md"]
        assert found[0].fetcher == "supplements"
        assert found[0].content_hash == doc_hash(
            "Divorce statistics and census methodology notes here.")
        again = await fetcher.fetch_url("supplements://notes.md")
        assert again == found[0]
        assert await fetcher.fetch_url("supplements://missing.md") is None
        assert await fetcher.fetch_url("https://example.com/x") is None
    finally:
        conn.close()


def test_registry_status(tmp_path: Path, monkeypatch) -> None:
    """T07.020: keyless fetchers ready; key-gated ones explain themselves."""
    monkeypatch.delenv("COURTLISTENER_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_FACTCHECK_KEY", raising=False)
    monkeypatch.delenv("TMDB_API_KEY", raising=False)
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        fetchers = build_fetchers(
            load_settings(CONFIG_DIR, env_file=None), conn, tmp_path / "cache")
        assert sorted(fetchers) == [
            "courtlistener", "crossref", "google_factcheck", "musicbrainz",
            "openalex", "openlibrary", "supplements", "tmdb", "web", "wikipedia",
        ]
        status = {s.name: s for s in fetcher_status(fetchers)}
        assert [n for n, s in sorted(status.items()) if s.enabled] == [
            "crossref", "musicbrainz", "openalex", "openlibrary", "supplements",
            "web", "wikipedia",
        ]
        assert status["courtlistener"].reason == "missing COURTLISTENER_TOKEN"
        assert status["google_factcheck"].reason == "missing GOOGLE_FACTCHECK_KEY"
        assert status["tmdb"].reason == "missing TMDB_API_KEY"
    finally:
        conn.close()
