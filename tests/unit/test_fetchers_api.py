"""P07 CourtListener + OpenAlex tests (T07.012/T07.013)."""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from sots.agents.failsafes.f03_circuit import CircuitBreaker
from sots.agents.failsafes.f14_politeness import PolitenessGate
from sots.config import load_settings
from sots.research.fetchers.base import FetcherDeps
from sots.research.fetchers.courtlistener import CourtlistenerFetcher
from sots.research.fetchers.crossref import CrossrefFetcher
from sots.research.fetchers.google_factcheck import GoogleFactcheckFetcher
from sots.research.fetchers.musicbrainz import ALLOWED_PATHS, MusicbrainzFetcher
from sots.research.fetchers.openalex import OpenAlexFetcher, reconstruct_abstract
from sots.research.fetchers.openlibrary import OpenlibraryFetcher
from sots.research.fetchers.tmdb import TmdbFetcher

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


def _deps(cache_dir: Path, name: str) -> FetcherDeps:
    return FetcherDeps(
        settings=load_settings(CONFIG_DIR, env_file=None),
        cache_dir=cache_dir,
        gate=PolitenessGate(rate_per_s=100.0, contact_email="t@t.test"),
        breaker=CircuitBreaker(key=f"test:{name}"),
    )


@respx.mock
async def test_courtlistener_lookup(tmp_path: Path) -> None:
    """T07.012 fixture 1: case search returns case cards."""
    route = respx.get("https://www.courtlistener.com/api/rest/v4/search/").mock(
        return_value=httpx.Response(200, json={"results": [
            {"case_name": "Roe v. Wade", "court": "SCOTUS",
             "date_filed": "1973-01-22", "docket_number": "70-18",
             "citation": "410 U.S. 113",
             "absolute_url": "/opinion/108713/roe-v-wade/",
             "snippet": "Abortion rights landmark."},
        ]})
    )
    fetcher = CourtlistenerFetcher(_deps(tmp_path / "cache", "cl"), "TOKEN")
    assert fetcher.enabled is True
    docs = await fetcher.lookup("Roe v Wade abortion")
    assert route.called
    assert [d.title for d in docs] == ["Roe v. Wade"]
    assert "410 U.S. 113" in docs[0].text
    assert "Abortion rights landmark." in docs[0].text
    assert docs[0].url == (
        "https://www.courtlistener.com/opinion/108713/roe-v-wade/")
    auth = route.calls[0].request.headers["Authorization"]
    assert auth == "Token TOKEN"


@respx.mock
async def test_courtlistener_opinion_and_docket(tmp_path: Path) -> None:
    """T07.012 fixture 2: opinion text + docket procedural history."""
    respx.get("https://www.courtlistener.com/api/rest/v4/opinions/108713/").mock(
        return_value=httpx.Response(200, json={
            "cluster": {"case_name": "Roe v. Wade", "court": "SCOTUS",
                        "date_filed": "1973-01-22", "citation": "410 U.S. 113"},
            "plain_text": "Held: the abortion decision is protected.",
        }))
    respx.get("https://www.courtlistener.com/api/rest/v4/dockets/456/").mock(
        return_value=httpx.Response(200, json={
            "case_name": "Roe v. Wade", "court": "SCOTUS",
            "date_filed": "1970-03-15", "docket_number": "70-18",
            "entries": [
                {"date_filed": "1970-03-15", "description": "Complaint filed."},
                {"date_filed": "1973-01-22", "description": "Judgment entered."},
            ],
        }))
    fetcher = CourtlistenerFetcher(_deps(tmp_path / "cache", "cl"), "TOKEN")
    opinion = await fetcher.fetch_url(
        "https://www.courtlistener.com/opinion/108713/roe-v-wade/")
    assert opinion is not None
    assert "abortion decision is protected" in opinion.text
    assert "Case: Roe v. Wade" in opinion.text
    docket = await fetcher.fetch_url("https://www.courtlistener.com/docket/456/x/")
    assert docket is not None
    assert "Complaint filed." in docket.text
    assert "Procedural history" in docket.text

    off = CourtlistenerFetcher(_deps(tmp_path / "cache", "cl"), None)
    assert off.enabled is False
    assert off.disabled_reason == "missing COURTLISTENER_TOKEN"
    assert await off.lookup("x") == []
    assert await off.fetch_url("https://www.courtlistener.com/opinion/1/") is None


def test_reconstruct_abstract() -> None:
    """T07.013: inverted-index reconstruction (+ empty)."""
    assert reconstruct_abstract({"the": [0, 3], "cat": [1], "sat": [2]}) == (
        "the cat sat the")
    assert reconstruct_abstract(None) == ""
    assert reconstruct_abstract({}) == ""


@respx.mock
async def test_openalex_lookup_and_fetch(tmp_path: Path, monkeypatch) -> None:
    """T07.013: works search + one work, abstract inline, mailto UA."""
    monkeypatch.setenv("CONTACT_EMAIL", "t@t.test")
    work = {
        "id": "https://openalex.org/W123", "title": "Rest Heals",
        "authorships": [{"author": {"display_name": "A. Researcher"}}],
        "publication_year": 2024,
        "primary_location": {"source": {"display_name": "J Rest"}},
        "doi": "https://doi.org/10.1000/rest",
        "cited_by_count": 42, "is_retracted": False,
        "abstract_inverted_index": {"rest": [0], "heals": [1], "minds": [2]},
    }
    search = respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": [work]}))
    respx.get("https://api.openalex.org/works/W123").mock(
        return_value=httpx.Response(200, json=work))
    fetcher = OpenAlexFetcher(_deps(tmp_path / "cache", "oa"))
    docs = await fetcher.lookup("rest heals")
    assert search.called
    assert "mailto:t@t.test" in search.calls[0].request.headers["User-Agent"]
    assert len(docs) == 1
    assert "Abstract: rest heals minds" in docs[0].text
    assert "Cited by: 42" in docs[0].text
    assert "Retracted: no" in docs[0].text
    one = await fetcher.fetch_url("https://openalex.org/W123")
    assert one is not None and one.title == "Rest Heals"
    assert await fetcher.fetch_url("https://example.com/x") is None


@respx.mock
async def test_crossref_updates_and_retraction(tmp_path: Path) -> None:
    """T07.014: update-to relations + retraction signals surface inline."""
    item = {
        "title": ["Rest Heals"], "DOI": "10.1000/rest",
        "author": [{"given": "A.", "family": "Researcher"}],
        "published": {"date-parts": [[2024]]},
        "relation": {"update-to": [{"id": "10.1000/rest-v2"}]},
        "subtype": "article",
    }
    respx.get("https://api.crossref.org/works").mock(
        return_value=httpx.Response(200, json={"message": {"items": [item]}}))
    respx.get("https://api.crossref.org/works/10.1000%2Frest").mock(
        return_value=httpx.Response(200, json={"message": item}))
    fetcher = CrossrefFetcher(_deps(tmp_path / "cache", "cr"))
    docs = await fetcher.lookup("rest heals")
    assert len(docs) == 1
    assert "DOI: 10.1000/rest" in docs[0].text
    assert "Updates: 10.1000/rest-v2" in docs[0].text
    assert "Retraction noticed: no" in docs[0].text
    bare = await fetcher.fetch_url("10.1000/rest")
    assert bare is not None and bare.title == "Rest Heals"
    assert await fetcher.fetch_url("https://example.com/x") is None


@respx.mock
async def test_google_factcheck_reviews(tmp_path: Path) -> None:
    """T07.015: claim search returns one doc per claimReview."""
    respx.get(
        "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    ).mock(return_value=httpx.Response(200, json={"claims": [
        {"text": "Vaccines contain chips.", "claimant": "A viral post",
         "claimReview": [
             {"url": "https://snopes.test/x", "title": "No chips",
              "textualRating": "False", "reviewDate": "2024-01-02",
              "publisher": {"name": "Snopes", "site": "snopes.test"}},
         ]},
    ]}))
    fetcher = GoogleFactcheckFetcher(_deps(tmp_path / "cache", "gfc"), "KEY")
    assert fetcher.enabled is True
    docs = await fetcher.lookup("vaccines chips")
    assert len(docs) == 1
    assert docs[0].url == "https://snopes.test/x"
    assert "Rating: False" in docs[0].text
    assert await fetcher.fetch_url("https://snopes.test/x") is None

    off = GoogleFactcheckFetcher(_deps(tmp_path / "cache", "gfc"), None)
    assert off.enabled is False
    assert await off.lookup("x") == []


@respx.mock
async def test_tmdb_details_and_credits(tmp_path: Path) -> None:
    """T07.016: search resolves, details + credits flesh out the doc."""
    respx.get("https://api.themoviedb.org/3/search/multi").mock(
        return_value=httpx.Response(200, json={"results": [
            {"media_type": "movie", "id": 11},
            {"media_type": "person", "id": 22},
        ]}))
    respx.get("https://api.themoviedb.org/3/movie/11").mock(
        return_value=httpx.Response(200, json={
            "title": "Test Film", "release_date": "2022-05-01",
            "overview": "A hero journeys far."}))
    respx.get("https://api.themoviedb.org/3/movie/11/credits").mock(
        return_value=httpx.Response(200, json={
            "crew": [{"name": "D. Rector", "job": "Director"}],
            "cast": [{"name": "A. Ctor"}, {"name": "B. Ctor"}]}))
    fetcher = TmdbFetcher(_deps(tmp_path / "cache", "tmdb"), "KEY")
    assert fetcher.enabled is True
    docs = await fetcher.lookup("Test Film")
    assert len(docs) == 1  # the person hit is skipped
    assert "Test Film (2022) [movie]" in docs[0].text
    assert "Director: D. Rector" in docs[0].text
    assert "A. Ctor" in docs[0].text
    one = await fetcher.fetch_url("https://www.themoviedb.org/movie/11-test-film")
    assert one is not None and one.title == "Test Film"

    off = TmdbFetcher(_deps(tmp_path / "cache", "tmdb"), None)
    assert off.enabled is False
    assert await off.lookup("x") == []


@respx.mock
async def test_openlibrary_work(tmp_path: Path) -> None:
    """T07.017: title search + work description, authors, year."""
    respx.get("https://openlibrary.org/search.json").mock(
        return_value=httpx.Response(200, json={"docs": [
            {"key": "/works/OL1W", "author_name": ["A. Uthor"],
             "first_publish_year": 1999},
        ]}))
    respx.get("https://openlibrary.org/works/OL1W.json").mock(
        return_value=httpx.Response(200, json={
            "title": "Test Book",
            "description": {"value": "A book about testing things."}}))
    fetcher = OpenlibraryFetcher(_deps(tmp_path / "cache", "ol"))
    docs = await fetcher.lookup("Test Book")
    assert len(docs) == 1
    assert "Authors: A. Uthor" in docs[0].text
    assert "First published: 1999" in docs[0].text
    assert "testing things" in docs[0].text
    one = await fetcher.fetch_url("https://openlibrary.org/works/OL1W")
    assert one is not None and one.title == "Test Book"


@respx.mock
async def test_musicbrainz_no_lyrics(tmp_path: Path) -> None:
    """T07.018: metadata only; the allowlist admits no lyric endpoint."""
    assert all("lyric" not in path for path in ALLOWED_PATHS)
    respx.get("https://musicbrainz.org/ws/2/recording/").mock(
        return_value=httpx.Response(200, json={"recordings": [
            {"id": "11111111-1111-1111-1111-111111111111", "title": "Test Song",
             "artist-credit": [{"name": "A. Singer"}],
             "releases": [{"title": "Test Album", "date": "2021"}]},
        ]}))
    fetcher = MusicbrainzFetcher(_deps(tmp_path / "cache", "mb"))
    docs = await fetcher.lookup("Test Song")
    assert len(docs) == 1
    assert "Artist: A. Singer" in docs[0].text
    assert "Test Album (2021)" in docs[0].text
