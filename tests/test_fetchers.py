"""Tests des fetchers avec transport HTTP mocké (httpx)."""

from __future__ import annotations

import pytest
import httpx

from citeright.fetchers.arxiv import fetch_arxiv
from citeright.fetchers.books import fetch_by_isbn
from citeright.fetchers.crossref import fetch_by_doi
from citeright.fetchers.openalex import fetch_by_title


@pytest.mark.asyncio
async def test_fetch_by_doi_crossref() -> None:
    payload = {
        "message": {
            "title": ["Test Article"],
            "author": [{"given": "Jane", "family": "Doe"}],
            "issued": {"date-parts": [[2020, 3, 1]]},
            "container-title": ["Journal of Testing"],
            "volume": "10",
            "issue": "2",
            "page": "100-110",
            "DOI": "10.1000/xyz",
            "type": "journal-article",
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "crossref.org" in str(request.url)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        meta = await fetch_by_doi("10.1000/xyz", client)

    assert meta["title"] == "Test Article"
    assert meta["doi"] == "10.1000/xyz"
    assert meta["year"] == 2020
    assert meta["journal"] == "Journal of Testing"
    assert len(meta["authors"]) == 1
    assert meta["authors"][0]["last"] == "Doe"


@pytest.mark.asyncio
async def test_fetch_by_title_openalex() -> None:
    payload = {
        "results": [
            {
                "title": "Attention Is All You Need",
                "publication_year": 2017,
                "authorships": [
                    {"author": {"display_name": "Ashish Vaswani"}},
                ],
                "host_venue": {"display_name": "NeurIPS"},
                "biblio": {
                    "volume": "1",
                    "issue": "",
                    "first_page": "1",
                    "last_page": "15",
                },
                "ids": {"doi": "https://doi.org/10.5555/123"},
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "openalex.org" in str(request.url)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        meta = await fetch_by_title("attention", client)

    assert "Attention" in meta["title"]
    assert meta["year"] == 2017
    assert meta["doi"] == "10.5555/123"


@pytest.mark.asyncio
async def test_fetch_arxiv_parses_atom() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <published>2017-06-12T17:57:34Z</published>
    <author><name>Ashish Vaswani</name></author>
    <summary>We propose a new network.</summary>
  </entry>
</feed>"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "arxiv.org" in str(request.url)
        return httpx.Response(200, text=xml)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        meta = await fetch_arxiv("1706.03762", client)

    assert "Attention" in meta["title"]
    assert meta["year"] == 2017
    assert meta["arxiv_id"] == "1706.03762"


@pytest.mark.asyncio
async def test_fetch_by_isbn_openlibrary() -> None:
    isbn = "9780134685991"
    payload = {
        f"ISBN:{isbn}": {
            "title": "Effective Java",
            "authors": [{"name": "Joshua Bloch"}],
            "publish_date": "2018",
            "publishers": [{"name": "Addison-Wesley"}],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "openlibrary.org" in str(request.url)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        meta = await fetch_by_isbn(isbn, client)

    assert "Effective Java" in meta["title"]
    assert meta["source_type"] == "book"
    assert meta["isbn"] == isbn
