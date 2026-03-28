"""Harvard (auteur-date), référence de bibliographie."""

from __future__ import annotations

from citeright.utils import normalize_authors


def _harv_author(a: dict[str, str]) -> str:
    last = (a.get("last") or "").strip() or "Unknown"
    first = (a.get("first") or "").strip()
    if first:
        ini = ", ".join(t[0].upper() + "." for t in first.split() if t)
        return f"{last}, {ini}" if ini else last
    return last


def _harv_authors(authors: list[dict[str, str]]) -> str:
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return _harv_author(authors[0])
    if len(authors) == 2:
        return f"{_harv_author(authors[0])} and {_harv_author(authors[1])}"
    return f"{_harv_author(authors[0])} et al."


def format_harvard(metadata: dict) -> str:
    """
    Formate une entrée Harvard (auteur-date).

    Args:
        metadata: Métadonnées normalisées.

    Returns:
        Ligne de bibliographie Harvard.
    """
    authors = normalize_authors(metadata.get("authors") or [])
    auth = _harv_authors(authors)
    year = metadata.get("year")
    year_s = str(year) if year is not None else "n.d."
    title = (metadata.get("title") or "Untitled").strip()
    st = (metadata.get("source_type") or "article").lower()

    if st == "book":
        pub = metadata.get("publisher") or "n.p."
        place = metadata.get("place") or ""
        loc = f"{place}: " if place else ""
        return f"{auth} ({year_s}) {title}. {loc}{pub}."

    if st in ("web", "webpage"):
        site = metadata.get("journal") or "Online"
        url = metadata.get("url") or ""
        return f"{auth} ({year_s}) '{title}', {site}. Available at: {url} (Accessed: n.d.)."

    journal = metadata.get("journal") or "Unknown journal"
    vol = metadata.get("volume") or ""
    issue = metadata.get("issue") or ""
    pages = metadata.get("pages") or ""

    tail = f"{journal}"
    if vol:
        tail += f", {vol}"
    if issue:
        tail += f"({issue})"
    if pages:
        tail += f", pp. {pages}"
    tail += f"."

    doi = metadata.get("doi")
    if doi:
        tail += f" doi:{doi}"
    elif metadata.get("url"):
        tail += f" Available at: {metadata['url']}"

    return f"{auth} ({year_s}) '{title}', {tail}"
