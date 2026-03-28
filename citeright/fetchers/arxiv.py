"""Client API arXiv (Atom/XML)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from citeright.utils import HTTP_TIMEOUT, normalize_authors


def _parse_arxiv_atom(xml_text: str, arxiv_id: str) -> dict[str, Any]:
    """Parse le flux Atom arXiv et retourne le schéma interne."""
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        entry = root.find("{http://www.w3.org/2005/Atom}entry")
    if entry is None:
        raise ValueError("Entrée arXiv introuvable dans le flux XML.")

    title = ""
    tit = entry.find("atom:title", ns)
    if tit is None:
        tit = entry.find("{http://www.w3.org/2005/Atom}title")
    if tit is not None and tit.text:
        title = " ".join(tit.text.split())

    authors_in: list[dict[str, str]] = []
    for author in entry.findall("atom:author", ns) + entry.findall(
        "{http://www.w3.org/2005/Atom}author"
    ):
        name_el = author.find("atom:name", ns)
        if name_el is None:
            name_el = author.find("{http://www.w3.org/2005/Atom}name")
        if name_el is not None and name_el.text:
            authors_in.append({"name": name_el.text.strip()})

    published = ""
    pub_el = entry.find("atom:published", ns)
    if pub_el is None:
        pub_el = entry.find("{http://www.w3.org/2005/Atom}published")
    if pub_el is not None and pub_el.text:
        published = pub_el.text[:10]

    year: int | None = None
    if len(published) >= 4 and published[:4].isdigit():
        year = int(published[:4])

    summary = ""
    sum_el = entry.find("atom:summary", ns)
    if sum_el is None:
        sum_el = entry.find("{http://www.w3.org/2005/Atom}summary")
    if sum_el is not None and sum_el.text:
        summary = " ".join(sum_el.text.split())[:500]

    id_el = entry.find("atom:id", ns)
    if id_el is None:
        id_el = entry.find("{http://www.w3.org/2005/Atom}id")
    abs_url = id_el.text.strip() if id_el is not None and id_el.text else ""

    doi = ""
    for link in entry.findall("atom:link", ns) + entry.findall(
        "{http://www.w3.org/2005/Atom}link"
    ):
        if link.get("title") == "doi":
            href = link.get("href") or ""
            if "doi.org/" in href:
                doi = href.split("doi.org/", 1)[-1]
            break

    meta: dict[str, Any] = {
        "title": title,
        "authors": normalize_authors(authors_in),
        "year": year,
        "journal": "arXiv preprint",
        "volume": "",
        "issue": "",
        "pages": "",
        "doi": doi,
        "url": abs_url or f"https://arxiv.org/abs/{arxiv_id}",
        "publisher": "arXiv",
        "source_type": "article",
        "arxiv_id": arxiv_id,
        "abstract_note": summary,
    }
    return meta


async def fetch_arxiv(
    arxiv_id: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """
    Récupère les métadonnées d'un article arXiv par identifiant (ex. 1706.03762).

    Args:
        arxiv_id: Identifiant sans préfixe arXiv: (version optionnelle acceptée puis ignorée).
        client: Client httpx async optionnel.

    Returns:
        Dict normalisé incluant arxiv_id et champs standards.

    Raises:
        httpx.HTTPError: Erreur réseau ou HTTP.
        ValueError: XML invalide ou entrée absente.
    """
    aid = arxiv_id.strip()
    if aid.lower().startswith("arxiv:"):
        aid = aid[6:].strip()
    if "v" in aid and aid.rsplit("v", 1)[-1].isdigit():
        aid = aid.rsplit("v", 1)[0]

    url = f"http://export.arxiv.org/api/query?id_list={aid}"

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        close_client = True
    try:
        response = await client.get(url)
        response.raise_for_status()
        return _parse_arxiv_atom(response.text, aid)
    finally:
        if close_client:
            await client.aclose()
