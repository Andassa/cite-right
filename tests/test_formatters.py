"""Tests unitaires des formatters avec métadonnées fixes."""

from __future__ import annotations

import pytest

from citeright.formatters.apa import format_apa
from citeright.formatters.chicago import format_chicago
from citeright.formatters.harvard import format_harvard
from citeright.formatters.ieee import format_ieee
from citeright.formatters.mla import format_mla
from citeright.formatters.vancouver import format_vancouver


@pytest.fixture
def article_meta() -> dict:
    """Article scientifique type."""
    return {
        "title": "Deep Learning for Science",
        "authors": [
            {"first": "Ada", "last": "Lovelace"},
            {"first": "Alan", "last": "Turing"},
        ],
        "year": 2021,
        "journal": "Nature Machine Intelligence",
        "volume": "3",
        "issue": "4",
        "pages": "300-310",
        "doi": "10.1038/s42256-021-00001-0",
        "url": "https://doi.org/10.1038/s42256-021-00001-0",
        "publisher": "",
        "source_type": "article",
    }


@pytest.fixture
def book_meta() -> dict:
    return {
        "title": "The Mythical Man-Month",
        "authors": [{"first": "Frederick P.", "last": "Brooks"}],
        "year": 1995,
        "journal": "",
        "volume": "",
        "issue": "",
        "pages": "",
        "doi": "",
        "url": "",
        "publisher": "Addison-Wesley",
        "source_type": "book",
    }


def test_format_apa_article(article_meta: dict) -> None:
    s = format_apa(article_meta)
    assert "Lovelace" in s and "Turing" in s
    assert "2021" in s
    assert "Nature Machine Intelligence" in s
    assert "10.1038" in s


def test_format_apa_book(book_meta: dict) -> None:
    s = format_apa(book_meta)
    assert "Brooks" in s
    assert "Mythical Man-Month" in s
    assert "Addison-Wesley" in s


def test_format_mla_article(article_meta: dict) -> None:
    s = format_mla(article_meta)
    assert "Lovelace" in s
    assert "Deep Learning" in s


def test_format_ieee_numbered(article_meta: dict) -> None:
    s = format_ieee(article_meta, index=2)
    assert s.startswith("[2]")
    assert "Deep Learning" in s


def test_format_chicago_article(article_meta: dict) -> None:
    s = format_chicago(article_meta)
    assert "2021" in s
    assert "Nature Machine Intelligence" in s


def test_format_vancouver(article_meta: dict) -> None:
    s = format_vancouver(article_meta, index=1)
    assert s.startswith("1.")
    assert "Lovelace" in s


def test_format_harvard(article_meta: dict) -> None:
    s = format_harvard(article_meta)
    assert "Lovelace" in s
    assert "(2021)" in s


def test_formatters_handle_missing_year() -> None:
    meta = {
        "title": "Untitled Work",
        "authors": [],
        "year": None,
        "journal": "",
        "volume": "",
        "issue": "",
        "pages": "",
        "doi": "",
        "url": "",
        "publisher": "",
        "source_type": "article",
    }
    assert "n.d." in format_apa(meta) or "Unknown" in format_apa(meta)
