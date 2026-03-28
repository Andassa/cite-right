"""Style Vancouver (numérotation implicite ; une entrée par ligne)."""

from __future__ import annotations

from citeright.utils import normalize_authors


def _van_name(a: dict[str, str]) -> str:
    last = (a.get("last") or "").strip() or "Unknown"
    first = (a.get("first") or "").strip()
    if not first:
        return last
    initials = " ".join(t[0].upper() for t in first.split() if t)
    return f"{last} {initials}"


def format_vancouver(metadata: dict, index: int | None = None) -> str:
    """
    Formate une référence Vancouver.

    Args:
        metadata: Métadonnées normalisées.
        index: Si fourni, préfixe la ligne par ce numéro (ex. mode liste).

    Returns:
        Ligne Vancouver.
    """
    authors = normalize_authors(metadata.get("authors") or [])
    if not authors:
        au = "Unknown."
    elif len(authors) <= 6:
        au = ", ".join(_van_name(a) for a in authors) + "."
    else:
        au = ", ".join(_van_name(a) for a in authors[:6]) + ", et al."

    title = (metadata.get("title") or "Untitled").strip()
    journal = metadata.get("journal") or ""
    year = metadata.get("year")
    year_s = str(year) if year is not None else "n.d."
    vol = metadata.get("volume") or ""
    issue = metadata.get("issue") or ""
    pages = metadata.get("pages") or ""

    parts: list[str] = []
    if index is not None:
        parts.append(f"{index}.")
    parts.append(au)
    parts.append(f"{title}.")
    if journal:
        j = journal
        if year:
            j += f" {year_s}"
        if vol:
            j += f";{vol}"
        if issue:
            j += f"({issue})"
        if pages:
            j += f":{pages.replace('-', '-')}"
        parts.append(j + ".")
    if metadata.get("doi"):
        parts.append(f"doi:{metadata['doi']}")
    elif metadata.get("url"):
        parts.append(f"Available from: {metadata['url']}")

    return " ".join(parts)
