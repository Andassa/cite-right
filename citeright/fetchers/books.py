"""Open Library : métadonnées livre par ISBN."""

from __future__ import annotations

import re
from typing import Any

import httpx

from citeright.utils import HTTP_TIMEOUT, normalize_authors, normalize_isbn_digits


def _parse_openlibrary(isbn: str, data: dict[str, Any]) -> dict[str, Any]:
    """Construit le dict normalisé depuis la réponse Open Library."""
    key = f"ISBN:{isbn}"
    book = data.get(key)
    if not isinstance(book, dict):
        raise ValueError("Réponse Open Library vide ou invalide pour cet ISBN.")

    title = str(book.get("title", "") or "")

    authors_in: list[dict[str, str]] = []
    for a in book.get("authors") or []:
        if isinstance(a, dict) and a.get("name"):
            authors_in.append({"name": str(a["name"])})

    year: int | None = None
    pub = book.get("publish_date", "")
    if isinstance(pub, str):
        m = re.search(r"(19|20)\d{2}", pub)
        if m:
            year = int(m.group(0))

    publishers = book.get("publishers") or []
    publisher = ""
    if publishers and isinstance(publishers[0], dict):
        publisher = str(publishers[0].get("name", "") or "")
    elif publishers and isinstance(publishers[0], str):
        publisher = publishers[0]

    url = str(book.get("url") or f"https://openlibrary.org/isbn/{isbn}")

    meta: dict[str, Any] = {
        "title": title,
        "authors": normalize_authors(authors_in),
        "year": year,
        "journal": "",
        "volume": "",
        "issue": "",
        "pages": "",
        "doi": "",
        "url": url,
        "publisher": publisher,
        "source_type": "book",
        "isbn": isbn,
    }
    return meta


async def fetch_by_isbn(
    isbn: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """
    Récupère les métadonnées d'un livre via l'API Open Library.

    Args:
        isbn: ISBN-10 ou ISBN-13 (tirets acceptés).
        client: Client httpx async optionnel.

    Returns:
        Dictionnaire normalisé avec source_type 'book' et clé isbn.

    Raises:
        httpx.HTTPError: Erreur HTTP.
        ValueError: ISBN inconnu ou JSON inattendu.
    """
    digits = normalize_isbn_digits(isbn)
    api_url = (
        "https://openlibrary.org/api/books"
        f"?bibkeys=ISBN:{digits}&format=json&jscmd=data"
    )

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        close_client = True
    try:
        response = await client.get(api_url)
        response.raise_for_status()
        payload = response.json()
        return _parse_openlibrary(digits, payload)
    finally:
        if close_client:
            await client.aclose()
