"""Format IEEE numéroté (une entrée avec préfixe [n])."""

from __future__ import annotations

from citeright.utils import normalize_authors


def _ieee_initial(a: dict[str, str]) -> str:
    """Initiales puis nom : A. B. Last."""
    first = (a.get("first") or "").strip()
    last = (a.get("last") or "").strip() or "Unknown"
    if not first:
        return last
    initials = ". ".join(t[0].upper() for t in first.split() if t) + "."
    return f"{initials} {last}"


def format_ieee(metadata: dict, index: int = 1) -> str:
    """
    Formate une référence IEEE avec numéro [n].

    Args:
        metadata: Métadonnées normalisées.
        index: Numéro de la référence (défaut 1).

    Returns:
        Ligne du type : [1] A. Author, "Title," Journal, ...
    """
    authors = normalize_authors(metadata.get("authors") or [])
    if not authors:
        au = "Unknown"
    elif len(authors) == 1:
        au = _ieee_initial(authors[0])
    else:
        au = ", ".join(_ieee_initial(a) for a in authors[:-1])
        au += f", and {_ieee_initial(authors[-1])}"

    title = (metadata.get("title") or "Untitled").strip()
    journal = metadata.get("journal") or ""
    vol = metadata.get("volume") or ""
    issue = metadata.get("issue") or ""
    pages = metadata.get("pages") or ""
    year = metadata.get("year")
    year_s = str(year) if year is not None else "n.d."

    body = f'[{index}] {au}, "{title}," '
    if journal:
        body += journal
        if vol:
            body += f", vol. {vol}"
        if issue:
            body += f", no. {issue}"
        if pages:
            body += f", pp. {pages}"
        body += f", {year_s}."
    else:
        body += f"{year_s}."
    if metadata.get("doi"):
        body += f" doi: {metadata['doi']}."
    elif metadata.get("url"):
        body += f" {metadata['url']}"
    return body.strip()
