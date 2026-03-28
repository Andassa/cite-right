"""Citation APA (7e édition), texte brut."""

from __future__ import annotations

from citeright.utils import normalize_authors


def _initials(first: str) -> str:
    """Convertit un prénom en initiales APA (J. K.)."""
    if not first:
        return ""
    tokens = first.replace(".", " ").split()
    parts = [t[0].upper() + "." for t in tokens if t]
    return " ".join(parts)


def _apa_one_author(author: dict[str, str]) -> str:
    """Formate un auteur : Nom, I. I."""
    last = (author.get("last") or "").strip() or "Unknown"
    first = (author.get("first") or "").strip()
    ini = _initials(first)
    if ini:
        return f"{last}, {ini}"
    return last


def _apa_authors_line(authors: list[dict[str, str]]) -> str:
    """Liste d'auteurs APA avec '&' avant le dernier."""
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return _apa_one_author(authors[0])
    if len(authors) == 2:
        return f"{_apa_one_author(authors[0])}, & {_apa_one_author(authors[1])}"
    parts = [_apa_one_author(a) for a in authors[:-1]]
    parts.append(f"& {_apa_one_author(authors[-1])}")
    return ", ".join(parts)


def _year_part(metadata: dict) -> str:
    y = metadata.get("year")
    if y is None:
        return "n.d."
    return str(y)


def format_apa(metadata: dict) -> str:
    """
    Produit une référence APA 7 (liste de références).

    Args:
        metadata: Schéma normalisé (title, authors, year, journal, etc.).

    Returns:
        Chaîne de citation sur une ou plusieurs lignes.
    """
    authors = normalize_authors(metadata.get("authors") or [])
    auth = _apa_authors_line(authors)
    year = _year_part(metadata)
    title = (metadata.get("title") or "Untitled").strip()
    st = (metadata.get("source_type") or "article").lower()

    if st == "book":
        pub = metadata.get("publisher") or "n.p."
        return f"{auth} ({year}). {title}. {pub}."

    if st in ("web", "webpage"):
        site = metadata.get("journal") or metadata.get("publisher") or "Site"
        url = metadata.get("url") or ""
        return f"{auth} ({year}). {title}. {site}. {url}".strip()

    # Article (défaut)
    journal = metadata.get("journal") or "Unknown journal"
    vol = metadata.get("volume") or ""
    issue = metadata.get("issue") or ""
    pages = metadata.get("pages") or ""
    doi = metadata.get("doi") or ""

    vol_issue = ""
    if vol and issue:
        vol_issue = f", {vol}({issue})"
    elif vol:
        vol_issue = f", {vol}"

    page_part = f", {pages}" if pages else ""
    tail = f"{vol_issue}{page_part}."
    if doi:
        tail += f" https://doi.org/{doi}"
    elif metadata.get("url"):
        tail += f" {metadata['url']}"

    return f"{auth} ({year}). {title}. {journal}{tail}"
