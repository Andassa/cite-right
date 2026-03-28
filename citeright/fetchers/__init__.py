"""Clients HTTP pour récupérer les métadonnées bibliographiques."""

from citeright.fetchers.arxiv import fetch_arxiv
from citeright.fetchers.books import fetch_by_isbn
from citeright.fetchers.crossref import fetch_by_doi
from citeright.fetchers.openalex import fetch_by_title

__all__ = [
    "fetch_arxiv",
    "fetch_by_doi",
    "fetch_by_isbn",
    "fetch_by_title",
]
