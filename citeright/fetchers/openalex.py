"""Client OpenAlex pour recherche par titre."""

from __future__ import annotations

from typing import Any

import httpx

from citeright.utils import HTTP_TIMEOUT, normalize_authors


def _parse_openalex_work(work: dict[str, Any]) -> dict[str, Any]:
    """Convertit un document OpenAlex en schéma interne."""
    title = str(work.get("title") or work.get("display_name") or "")

    authors_in: list[dict[str, str]] = []
    for authorship in work.get("authorships") or []:
        au = authorship.get("author") or {}
        display = au.get("display_name")
        if display:
            authors_in.append({"name": str(display)})

    year = work.get("publication_year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = None

    venue = ""
    host = work.get("host_venue") or work.get("primary_location") or {}
    if isinstance(host, dict):
        venue = str(host.get("display_name") or "")

    biblio = work.get("biblio") or {}
    volume = str(biblio.get("volume", "") or "")
    issue = str(biblio.get("issue", "") or "")
    first_page = biblio.get("first_page") or ""
    last_page = biblio.get("last_page") or ""
    pages = ""
    if first_page and last_page:
        pages = f"{first_page}-{last_page}"
    elif first_page:
        pages = str(first_page)

    ids = work.get("ids") or {}
    doi = str(ids.get("doi") or "")
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")

    url = str(work.get("id") or "")
    if doi:
        url = f"https://doi.org/{doi}"

    meta: dict[str, Any] = {
        "title": title,
        "authors": normalize_authors(authors_in),
        "year": year,
        "journal": venue,
        "volume": volume,
        "issue": issue,
        "pages": pages,
        "doi": doi,
        "url": url,
        "publisher": "",
        "source_type": "article",
    }
    concepts = work.get("concepts") or []
    if concepts:
        meta["openalex_concepts"] = [
            (c.get("display_name") or "") for c in concepts[:5] if isinstance(c, dict)
        ]
    return meta


async def fetch_by_title(
    title: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """
    Recherche une œuvre par titre (meilleur match, per-page=1).

    Args:
        title: Titre ou portion de titre.
        client: Client httpx async optionnel.

    Returns:
        Dictionnaire normalisé (même schéma que CrossRef).

    Raises:
        httpx.HTTPStatusError: Erreur HTTP.
        ValueError: Aucun résultat ou JSON inattendu.
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        close_client = True
    try:
        response = await client.get(
            "https://api.openalex.org/works",
            params={"search": title.strip(), "per-page": 1},
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results")
        if not results:
            raise ValueError("Aucun résultat OpenAlex pour ce titre.")
        work = results[0]
        if not isinstance(work, dict):
            raise ValueError("Résultat OpenAlex invalide.")
        return _parse_openalex_work(work)
    finally:
        if close_client:
            await client.aclose()
