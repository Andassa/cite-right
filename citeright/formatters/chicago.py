"""Chicago 17e (auteur-date), référence de fin de texte."""

from __future__ import annotations

from citeright.utils import normalize_authors


def _chi_author(a: dict[str, str]) -> str:
    last = (a.get("last") or "").strip() or "Unknown"
    first = (a.get("first") or "").strip()
    if first:
        return f"{last}, {first}"
    return last


def _chi_authors(authors: list[dict[str, str]]) -> str:
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return _chi_author(authors[0])
    if len(authors) == 2:
        return f"{_chi_author(authors[0])}, and {_chi_author(authors[1])}"
    return f"{_chi_author(authors[0])} et al."


def format_chicago(metadata: dict) -> str:
    """
    Formate une entrée Chicago auteur-date (bibliographie).

    Args:
        metadata: Métadonnées normalisées.

    Returns:
        Référence Chicago auteur-date.

    Note:
        Le style note de bas de page complet nécessiterait des appels de note séparés ;
        ici on fournit l'équivalent bibliographie auteur-date.
    """
    authors = normalize_authors(metadata.get("authors") or [])
    auth = _chi_authors(authors)
    year = metadata.get("year")
    year_s = str(year) if year is not None else "n.d."
    title = (metadata.get("title") or "Untitled").strip()
    st = (metadata.get("source_type") or "article").lower()

    if st == "book":
        place = metadata.get("place") or ""
        pub = metadata.get("publisher") or "n.p."
        place_pub = f"{place}: {pub}" if place else pub
        return f"{auth}. {year_s}. {title}. {place_pub}."

    if st in ("web", "webpage"):
        site = metadata.get("journal") or ""
        url = metadata.get("url") or ""
        extra = f" {site}." if site else ""
        return f'{auth}. {year_s}. "{title}."{extra} Accessed via {url}.'

    journal = metadata.get("journal") or "Unknown journal"
    vol = metadata.get("volume") or ""
    issue = metadata.get("issue") or ""
    pages = metadata.get("pages") or ""

    bib = f'{auth}. {year_s}. "{title}." {journal}'
    if vol:
        bib += f" {vol}"
    if issue:
        bib += f", no. {issue}"
    if pages:
        bib += f": {pages}"
    bib += "."
    if metadata.get("doi"):
        bib += f" https://doi.org/{metadata['doi']}."
    elif metadata.get("url"):
        bib += f" {metadata['url']}."
    return bib
