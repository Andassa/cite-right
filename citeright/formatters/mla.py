"""Citation MLA (9e édition), entrée Works Cited."""

from __future__ import annotations

from citeright.utils import normalize_authors


def _mla_author_one(a: dict[str, str]) -> str:
    last = (a.get("last") or "").strip() or "Unknown"
    first = (a.get("first") or "").strip()
    if first:
        return f"{last}, {first}"
    return last


def _mla_authors(authors: list[dict[str, str]]) -> str:
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return _mla_author_one(authors[0])
    if len(authors) == 2:
        a0, a1 = authors[0], authors[1]
        f0 = (a0.get("first") or "").strip()
        f1 = (a1.get("first") or "").strip()
        l0 = (a0.get("last") or "").strip() or "Unknown"
        l1 = (a1.get("last") or "").strip() or "Unknown"
        if f0 and f1:
            return f"{l0}, {f0}, and {f1} {l1}"
        return f"{_mla_author_one(a0)}, and {_mla_author_one(a1)}"
    first = _mla_author_one(authors[0])
    others = ", ".join(
        f"{(x.get('first') or '').strip()} {(x.get('last') or '').strip()}".strip()
        or (x.get("last") or "Unknown")
        for x in authors[1:]
    )
    return f"{first}, et al." if len(authors) > 3 else f"{first}, {others}"


def format_mla(metadata: dict) -> str:
    """
    Formate une entrée MLA 9 (Works Cited).

    Args:
        metadata: Métadonnées normalisées.

    Returns:
        Ligne(s) de citation MLA.
    """
    authors = normalize_authors(metadata.get("authors") or [])
    auth = _mla_authors(authors)
    title = (metadata.get("title") or "Untitled").strip()
    year = metadata.get("year")
    year_s = str(year) if year is not None else "n.d."
    st = (metadata.get("source_type") or "article").lower()

    if st == "book":
        pub = metadata.get("publisher") or "n.p."
        return f"{auth}. {title}. {pub}, {year_s}."

    if st in ("web", "webpage"):
        site = metadata.get("journal") or "Web"
        url = metadata.get("url") or ""
        return f'{auth}. "{title}." {site}, {year_s}, {url}.'

    journal = metadata.get("journal") or "Unknown"
    vol = metadata.get("volume") or ""
    issue = metadata.get("issue") or ""
    pages = metadata.get("pages") or ""

    core = f'{auth}. "{title}." {journal}'
    if vol:
        core += f", vol. {vol}"
    if issue:
        core += f", no. {issue}"
    if pages:
        core += f", pp. {pages}"
    core += f", {year_s}"
    if metadata.get("doi"):
        core += f", doi:{metadata['doi']}"
    elif metadata.get("url"):
        core += f", {metadata['url']}"
    core += "."
    return core
