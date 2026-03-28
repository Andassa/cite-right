"""Client CrossRef pour résolution par DOI."""

from __future__ import annotations

from typing import Any

import httpx

from citeright.utils import HTTP_TIMEOUT, clean_doi, normalize_authors


def _first_list_item(msg: dict[str, Any], key: str) -> str:
    """Extrait le premier élément d'une liste de chaînes CrossRef (souvent sous clé)."""
    raw = msg.get(key)
    if isinstance(raw, list) and raw:
        first = raw[0]
        if isinstance(first, str):
            return first
    return ""


def _parse_crossref_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Mappe le message 'message' CrossRef vers le schéma interne."""
    title = _first_list_item(msg, "title") or msg.get("title", "") or ""
    if isinstance(title, list):
        title = title[0] if title else ""

    authors_in: list[Any] = []
    for a in msg.get("author") or []:
        if isinstance(a, dict):
            authors_in.append(
                {
                    "given": a.get("given", ""),
                    "family": a.get("family", ""),
                }
            )

    issued = (msg.get("issued") or {}).get("date-parts") or []
    year: int | None = None
    if issued and issued[0]:
        try:
            year = int(issued[0][0])
        except (TypeError, ValueError, IndexError):
            year = None

    container = msg.get("container-title")
    journal = ""
    if isinstance(container, list) and container:
        journal = str(container[0])
    elif isinstance(container, str):
        journal = container

    volume = str(msg.get("volume", "") or "")
    issue = str(msg.get("issue", "") or "")
    page = str(msg.get("page", "") or "")

    doi = str(msg.get("DOI", "") or msg.get("doi", "") or "")
    url = ""
    link = msg.get("URL")
    if isinstance(link, str):
        url = link
    if not url and doi:
        url = f"https://doi.org/{doi}"

    publisher = ""
    pub = msg.get("publisher")
    if isinstance(pub, str):
        publisher = pub

    st = "article"
    t = (msg.get("type") or "").lower()
    if t in ("book", "book-chapter", "monograph"):
        st = "book"
    elif t in ("dataset", "software", "report"):
        st = "article"

    meta: dict[str, Any] = {
        "title": title,
        "authors": normalize_authors(authors_in),
        "year": year,
        "journal": journal,
        "volume": volume,
        "issue": issue,
        "pages": page,
        "doi": doi,
        "url": url,
        "publisher": publisher,
        "source_type": st,
    }
    return meta


async def fetch_by_doi(
    doi: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """
    Récupère les métadonnées d'une œuvre via l'API CrossRef.

    Args:
        doi: Identifiant DOI (avec ou sans préfixe https://doi.org/).
        client: Client httpx async réutilisable.

    Returns:
        Dictionnaire normalisé (title, authors, year, journal, volume, issue,
        pages, doi, url, publisher, source_type).

    Raises:
        httpx.HTTPStatusError: Si la réponse HTTP indique une erreur.
        httpx.RequestError: En cas d'échec réseau / timeout.
        ValueError: Si le corps JSON est inattendu.
    """
    clean = clean_doi(doi)
    api_url = f"https://api.crossref.org/works/{clean}"

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        close_client = True
    try:
        response = await client.get(
            api_url,
            headers={"User-Agent": "cite-right/0.1 (mailto:example@example.com)"},
        )
        response.raise_for_status()
        payload = response.json()
        msg = payload.get("message")
        if not isinstance(msg, dict):
            raise ValueError("Réponse CrossRef invalide : champ 'message' absent.")
        return _parse_crossref_message(msg)
    finally:
        if close_client:
            await client.aclose()
