"""P03 tool tests part 2 (T03.021-T03.022, T03.027-T03.030): web, db, stubs."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
import yaml

from sots.agents.tools import excerpt_verify as excerpt_mod
from sots.agents.tools import fetch_url as fetch_mod
from sots.agents.tools import web_search as search_mod
from sots.agents.tools.base import ToolContext, get_tool, registered_tools
from sots.agents.tools.db_read import (
    DbReadEvidenceArgs,
    DbReadFindingsArgs,
    DbReadProfileArgs,
    DbReadUnitsArgs,
)
from sots.agents.tools.fetch_url import FetchUrlArgs
from sots.agents.tools.structured_lookups import LOOKUP_TOOLS
from sots.agents.tools.web_search import (
    WebSearchArgs,
    clear_search_providers,
    register_search_provider,
)
from sots.config import load_settings
from sots.models.evidence import Evidence, SearchHit
from sots.models.unit import Unit
from sots.models.verdict import SpecialistFindings
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _ctx(tmp_path: Path, conn=None, profile_dir: str = "profile") -> ToolContext:
    return ToolContext(
        run_id="run_1", document_id="doc_1",
        settings=load_settings(CONFIG_DIR, env_file=None),
        conn=conn, data_dir=str(tmp_path / "data"), profile_dir=profile_dir,
    )


class _FakeSearch:
    def __init__(self, name: str, hits: list[SearchHit] | Exception) -> None:
        self.name = name
        self._hits = hits
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        self.calls.append((query, max_results))
        if isinstance(self._hits, Exception):
            raise self._hits
        return self._hits


def _hit(i: int) -> SearchHit:
    return SearchHit(url=f"https://x.test/{i}", title=f"T{i}", snippet=f"S{i}", rank=i)


# --- T03.021: web_search ---


async def test_web_search_chain_and_cap(tmp_path: Path) -> None:
    before = dict(search_mod.registered_search_providers())
    try:
        clear_search_providers()
        down = _FakeSearch("searxng", RuntimeError("boom"))
        good = _FakeSearch("tavily", [_hit(i) for i in range(20)])
        register_search_provider(down)
        register_search_provider(good)
        tool = get_tool("web_search")
        assert tool.internet is True
        obs = await tool.run(WebSearchArgs(query="q", max_results=50), _ctx(tmp_path))
        assert obs.ok
        payload = json.loads(obs.content)
        assert payload["provider"] == "tavily"
        assert len(payload["hits"]) == 10  # clamped
        assert good.calls == [("q", 10)]
        assert any("searxng" in note for note in payload["skipped"])
    finally:
        clear_search_providers()
        for provider in before.values():
            register_search_provider(provider)


async def test_web_search_all_fail(tmp_path: Path) -> None:
    before = dict(search_mod.registered_search_providers())
    try:
        clear_search_providers()
        obs = await get_tool("web_search").run(WebSearchArgs(query="q"), _ctx(tmp_path))
        assert obs.ok is False and "not registered" in obs.content
    finally:
        clear_search_providers()
        for provider in before.values():
            register_search_provider(provider)


@respx.mock
async def test_web_search_respx_backend(tmp_path: Path) -> None:
    class _HttpSearch:
        name = "searxng"

        async def search(self, query: str, max_results: int):
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://search.test/", params={"q": query, "n": max_results}
                )
                response.raise_for_status()
            return [SearchHit(url="http://x", title="T", snippet="S", rank=1)]

    before = dict(search_mod.registered_search_providers())
    try:
        clear_search_providers()
        register_search_provider(_HttpSearch())
        route = respx.get("http://search.test/").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        obs = await get_tool("web_search").run(WebSearchArgs(query="hi"), _ctx(tmp_path))
        assert obs.ok and route.called
    finally:
        clear_search_providers()
        for provider in before.values():
            register_search_provider(provider)


# --- T03.022: fetch_url ---

HTML_PAGE = """<html><head><title> ignored</title></head><body><article>
<h1>Civic Decline</h1><p>First paragraph about civic life and its troubles.</p>
<p>Second paragraph with more detail on the same important topic.</p>
<p>Third paragraph concluding the argument with evidence and care.</p>
</article></body></html>"""


@respx.mock
async def test_fetch_url_html_caches_and_previews(tmp_path: Path) -> None:
    respx.get("http://site.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow:\n")
    )
    route = respx.get("http://site.test/page").mock(
        return_value=httpx.Response(200, text=HTML_PAGE, headers={"content-type": "text/html"})
    )
    obs = await get_tool("fetch_url").run(FetchUrlArgs(url="http://site.test/page"), _ctx(tmp_path))
    assert obs.ok, obs.content
    assert route.called
    assert route.calls[0].request.headers["User-Agent"].startswith("SotS research fetcher")
    payload = json.loads(obs.content)
    assert payload["publisher"] == "site.test"
    assert "civic" in payload["text_preview"].lower()
    cache_file = Path(payload["cache"])
    assert cache_file.is_file()
    cached = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached["content_hash"] == payload["content_hash"]
    assert len(cached["text"]) >= len(payload["text_preview"])


@respx.mock
async def test_fetch_url_robots_pdf_errors_and_caps(tmp_path: Path) -> None:
    respx.get("http://blocked.test/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
    )
    blocked = await get_tool("fetch_url").run(
        FetchUrlArgs(url="http://blocked.test/x"), _ctx(tmp_path)
    )
    assert blocked.ok is False and "robots.txt" in blocked.content

    pdf_bytes = b"%PDF-1.4 fake body"
    respx.get("http://files.test/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("http://files.test/doc.pdf").mock(
        return_value=httpx.Response(
            200, content=pdf_bytes, headers={"content-type": "application/pdf"}
        )
    )
    pdf = await get_tool("fetch_url").run(
        FetchUrlArgs(url="http://files.test/doc.pdf"), _ctx(tmp_path)
    )
    assert pdf.ok
    payload = json.loads(pdf.content)
    assert payload["note"].startswith("PDF bytes cached")
    assert Path(payload["cache"]).suffix == ".pdf"

    bad = await get_tool("fetch_url").run(FetchUrlArgs(url="ftp://x/y"), _ctx(tmp_path))
    assert bad.ok is False and "http/https" in bad.content

    respx.get("http://img.test/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("http://img.test/a.png").mock(
        return_value=httpx.Response(200, content=b"PNG", headers={"content-type": "image/png"})
    )
    img = await get_tool("fetch_url").run(FetchUrlArgs(url="http://img.test/a.png"), _ctx(tmp_path))
    assert img.ok is False and "unsupported content-type" in img.content


@respx.mock
async def test_fetch_url_size_cap(tmp_path: Path) -> None:
    respx.get("http://big.test/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("http://big.test/huge").mock(
        return_value=httpx.Response(200, content=b"x" * (fetch_mod.MAX_BYTES + 1),
                                    headers={"content-type": "text/html"})
    )
    obs = await get_tool("fetch_url").run(FetchUrlArgs(url="http://big.test/huge"), _ctx(tmp_path))
    assert obs.ok is False and "exceeds" in obs.content


# --- T03.027: db_read ---


def _seed_db(tmp_path: Path):
    from datetime import datetime

    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    own = Unit(
        id="u_own", document_id="doc_1", chunk_id="c1", run_id="run_1", order=0,
        text="own text", start_char=0, end_char=8,
    )
    other_run = Unit(
        id="u_other_run", document_id="doc_1", chunk_id="c1", run_id="run_2", order=0,
        text="other run", start_char=0, end_char=9,
    )
    other_doc = Unit(
        id="u_other_doc", document_id="doc_9", chunk_id="c9", run_id="run_1", order=0,
        text="other doc", start_char=0, end_char=9,
    )
    for unit in (own, other_run, other_doc):
        storage_repo.save_unit(conn, unit)
    storage_repo.save_evidence(
        conn,
        Evidence(
            id="e1", unit_id="u_own", url="http://x", title="T", publisher=None,
            published_date=None, accessed_at=datetime(2026, 1, 1), source_class="journalism",
            tier=3, excerpt="ex", excerpt_match_score=1.0, stance="supports",
            fetcher="web", content_hash="h",
        ),
    )
    storage_repo.save_specialist_findings(
        conn, SpecialistFindings(unit_id="u_own", specialist="stats")
    )
    return conn


async def test_db_read_units_scoped(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path)
    try:
        tool = get_tool("db_read_units")
        ok = await tool.run(DbReadUnitsArgs(unit_ids=["u_own", "u_missing"]), _ctx(tmp_path, conn))
        assert ok.ok
        payload = json.loads(ok.content)
        assert [u["id"] for u in payload["units"]] == ["u_own"]
        assert payload["missing"] == ["u_missing"]
        cross_run = await tool.run(DbReadUnitsArgs(unit_ids=["u_other_run"]), _ctx(tmp_path, conn))
        assert cross_run.ok is False and "u_other_run" in cross_run.content
        cross_doc = await tool.run(DbReadUnitsArgs(unit_ids=["u_other_doc"]), _ctx(tmp_path, conn))
        assert cross_doc.ok is False and "u_other_doc" in cross_doc.content
        no_conn = await tool.run(DbReadUnitsArgs(unit_ids=["u_own"]), _ctx(tmp_path))
        assert no_conn.ok is False and "no database" in no_conn.content
    finally:
        conn.close()


async def test_db_read_evidence_findings_scoped(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path)
    try:
        ctx = _ctx(tmp_path, conn)
        ev = await get_tool("db_read_evidence").run(DbReadEvidenceArgs(unit_ids=["u_own"]), ctx)
        assert ev.ok and '"id": "e1"' in ev.content
        ev_none = await get_tool("db_read_evidence").run(DbReadEvidenceArgs(), ctx)
        assert ev_none.ok is False and "unit_ids" in ev_none.content
        denied = await get_tool("db_read_evidence").run(
            DbReadEvidenceArgs(unit_ids=["u_other_run"]), ctx
        )
        assert denied.ok is False and "u_other_run" in denied.content
        findings = await get_tool("db_read_findings").run(
            DbReadFindingsArgs(unit_ids=["u_own"]), ctx
        )
        assert findings.ok and "stats" in findings.content
        denied_f = await get_tool("db_read_findings").run(
            DbReadFindingsArgs(unit_ids=["u_other_doc"]), ctx
        )
        assert denied_f.ok is False and "u_other_doc" in denied_f.content
    finally:
        conn.close()


async def test_db_read_profile(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "messages.yaml").write_text(
        yaml.safe_dump({"book": [{"id": "M1"}], "chapters": {"ch01": [{"id": "C1"}]}}),
        encoding="utf-8",
    )
    ctx = _ctx(tmp_path, profile_dir=str(profile))
    book = await get_tool("db_read_profile").run(DbReadProfileArgs(), ctx)
    assert book.ok and "M1" in book.content
    chapter = await get_tool("db_read_profile").run(DbReadProfileArgs(chapter="ch01"), ctx)
    assert chapter.ok and "C1" in chapter.content
    unknown = await get_tool("db_read_profile").run(DbReadProfileArgs(chapter="ch99"), ctx)
    assert unknown.ok is False and "ch99" in unknown.content
    no_profile = _ctx(tmp_path, profile_dir=str(tmp_path / "no-profile"))
    missing = await get_tool("db_read_profile").run(DbReadProfileArgs(), no_profile)
    assert missing.ok is False and "messages.yaml" in missing.content


# --- T03.028-T03.030: stubs ---


def test_excerpt_verify_interface() -> None:
    import inspect

    assert list(inspect.signature(excerpt_mod.verify_excerpt).parameters) == ["doc_text", "excerpt"]
    with pytest.raises(NotImplementedError, match="P07"):
        excerpt_mod.verify_excerpt("doc", "ex")


async def test_excerpt_verify_tool_reports_stub(tmp_path: Path) -> None:
    obs = await get_tool("excerpt_verify").run(
        excerpt_mod.ExcerptVerifyArgs(doc_text="d", excerpt="e"), _ctx(tmp_path)
    )
    assert obs.ok is False and "P07" in obs.content


def test_lookup_and_languagetool_listed() -> None:
    names = registered_tools()
    assert len(LOOKUP_TOOLS) == 8
    for name in LOOKUP_TOOLS:
        assert name in names
        assert names[name].internet is True
    assert "languagetool" in names


async def test_lookup_and_languagetool_report_stubs(tmp_path: Path) -> None:
    from sots.agents.tools.languagetool import LanguageToolArgs
    from sots.agents.tools.structured_lookups import LookupArgs

    obs = await get_tool("courtlistener").run(LookupArgs(query="q"), _ctx(tmp_path))
    assert obs.ok is False and "P07" in obs.content
    obs2 = await get_tool("languagetool").run(LanguageToolArgs(text="t"), _ctx(tmp_path))
    assert obs2.ok is False and "P15" in obs2.content
