"""Utilitaires : détection d'entrée, cache SQLite, export BibTeX/RIS, presse-papier."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Literal

import httpx
import pyperclip

# Timeout commun pour les appels HTTP (secondes).
HTTP_TIMEOUT = 10.0

# Fichier de cache dans le répertoire de travail courant.
DEFAULT_CACHE_PATH = Path(".cite-right-cache.db")

InputType = Literal["doi", "arxiv", "isbn", "url", "title"]

_DOI_PATTERN = re.compile(r"^10\.\d{4,}/\S+$", re.IGNORECASE)
_ARXIV_ABS = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(?P<id>[\d.]+)(?:v\d+)?",
    re.IGNORECASE,
)
_ARXIV_ID = re.compile(r"^(?:arxiv:)?(?P<id>\d{4}\.\d{4,5})(?:v\d+)?$", re.IGNORECASE)
_URL_START = re.compile(r"^https?://", re.IGNORECASE)


def get_cache_path() -> Path:
    """Retourne le chemin du fichier SQLite de cache."""
    return DEFAULT_CACHE_PATH


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_cache_path()
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    return conn


def cache_get(key: str, db_path: Path | None = None) -> dict[str, Any] | None:
    """
    Récupère une entrée du cache JSON par clé.

    Args:
        key: Clé stable (ex. préfixe + identifiant).
        db_path: Chemin optionnel vers la base SQLite.

    Returns:
        Dictionnaire des métadonnées ou None si absent.
    """
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        return json.loads(row[0])
    finally:
        conn.close()


def cache_set(key: str, data: dict[str, Any], db_path: Path | None = None) -> None:
    """
    Enregistre des métadonnées dans le cache.

    Args:
        key: Clé stable.
        data: Métadonnées sérialisables en JSON.
        db_path: Chemin optionnel vers la base SQLite.
    """
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)",
            (key, json.dumps(data, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def validate_doi(doi: str) -> bool:
    """
    Valide le format d'un DOI (préfixe Crossref attendu).

    Args:
        doi: Chaîne DOI brute (sans préfixe https://doi.org/ si possible).

    Returns:
        True si le format est valide pour l'appel API.
    """
    cleaned = doi.strip()
    cleaned = re.sub(r"^https?://(dx\.)?doi\.org/", "", cleaned, flags=re.I)
    return bool(_DOI_PATTERN.match(cleaned.strip()))


def _isbn10_check(isbn10: str) -> bool:
    if len(isbn10) != 10:
        return False
    total = 0
    for i, ch in enumerate(isbn10[:9]):
        if not ch.isdigit():
            return False
        total += int(ch) * (10 - i)
    last = isbn10[9]
    if last.upper() == "X":
        total += 10
    elif last.isdigit():
        total += int(last)
    else:
        return False
    return total % 11 == 0


def _isbn13_check(isbn13: str) -> bool:
    if len(isbn13) != 13 or not isbn13.isdigit():
        return False
    total = sum(int(isbn13[i]) * (1 if i % 2 == 0 else 3) for i in range(12))
    check = (10 - (total % 10)) % 10
    return check == int(isbn13[12])


def validate_isbn(raw: str) -> bool:
    """
    Valide un ISBN-10 ou ISBN-13 (chiffres et tirets / espaces ignorés).

    Args:
        raw: ISBN saisi par l'utilisateur.

    Returns:
        True si la checksum est correcte.
    """
    digits = re.sub(r"[\s\-]", "", raw.strip())
    if len(digits) == 10:
        return _isbn10_check(digits.upper())
    if len(digits) == 13:
        return _isbn13_check(digits)
    return False


def normalize_isbn_digits(raw: str) -> str:
    """Retourne uniquement les chiffres (et X final pour ISBN-10) d'un ISBN."""
    s = re.sub(r"[\s\-]", "", raw.strip())
    return s.upper()


def detect_input_type(user_input: str) -> InputType:
    """
    Déduit le type de source à partir d'une chaîne brute.

    Args:
        user_input: DOI, URL, ISBN, identifiant arXiv ou titre libre.

    Returns:
        Un des littéraux : doi, arxiv, isbn, url, title.
    """
    s = user_input.strip()
    if not s:
        return "title"
    if _URL_START.match(s):
        if "arxiv.org" in s.lower():
            return "arxiv"
        return "url"
    doi_candidate = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I).strip()
    if _DOI_PATTERN.match(doi_candidate):
        return "doi"
    digits = normalize_isbn_digits(s)
    if len(digits) in (10, 13) and digits[:-1].isdigit() and (
        digits[-1].isdigit() or digits[-1] == "X"
    ):
        if validate_isbn(s):
            return "isbn"
    if _ARXIV_ID.match(s):
        return "arxiv"
    return "title"


def normalize_authors(raw_authors: list[Any]) -> list[dict[str, str]]:
    """
    Normalise une liste d'auteurs hétérogène en prénoms / noms.

    Args:
        raw_authors: Éléments issus des APIs (dict avec clés variables ou chaînes).

    Returns:
        Liste de {"first": str, "last": str}.
    """
    out: list[dict[str, str]] = []
    if not raw_authors:
        return out
    for item in raw_authors:
        if isinstance(item, str):
            parts = item.strip().split()
            if len(parts) >= 2:
                out.append({"first": " ".join(parts[:-1]), "last": parts[-1]})
            elif parts:
                out.append({"first": "", "last": parts[0]})
            continue
        if not isinstance(item, dict):
            continue
        if "family" in item or "given" in item:
            out.append(
                {
                    "first": str(item.get("given", "")).strip(),
                    "last": str(item.get("family", "")).strip(),
                }
            )
            continue
        if "last" in item or "first" in item:
            out.append(
                {
                    "first": str(item.get("first", "")).strip(),
                    "last": str(item.get("last", "")).strip(),
                }
            )
            continue
        name = item.get("name") or item.get("display_name") or ""
        if name:
            parts = str(name).strip().split()
            if len(parts) >= 2:
                out.append({"first": " ".join(parts[:-1]), "last": parts[-1]})
            else:
                out.append({"first": "", "last": str(name)})
    return [a for a in out if a.get("last") or a.get("first")]


def copy_to_clipboard(text: str) -> bool:
    """
    Copie du texte dans le presse-papier système.

    Args:
        text: Contenu à copier.

    Returns:
        True en cas de succès, False si pyperclip échoue (headless, etc.).
    """
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def export_bibtex(metadata: dict[str, Any], style: str = "generic") -> str:
    """
    Génère une entrée BibTeX à partir des métadonnées normalisées.

    Args:
        metadata: Dict avec title, authors, year, journal, volume, issue, pages, doi, etc.
        style: Ignoré pour l'instant ; réservé pour variantes par style.

    Returns:
        Chaîne .bib (une entrée).
    """
    _ = style
    key = _bibtex_cite_key(metadata)
    typ = metadata.get("bibtex_type") or _guess_bibtex_type(metadata)
    fields: list[tuple[str, str]] = []
    title = metadata.get("title") or "Unknown title"
    fields.append(("title", _bibtex_brace(title)))
    authors = normalize_authors(metadata.get("authors") or [])
    if authors:
        au = " and ".join(
            f"{a.get('last', '')}, {a.get('first', '')}".strip(", ")
            for a in authors
        )
        fields.append(("author", _bibtex_brace(au)))
    year = metadata.get("year")
    if year:
        fields.append(("year", str(year)))
    journal = metadata.get("journal") or metadata.get("container_title")
    if journal and typ == "article":
        fields.append(("journal", _bibtex_brace(journal)))
    if metadata.get("volume"):
        fields.append(("volume", str(metadata["volume"])))
    if metadata.get("issue"):
        fields.append(("number", str(metadata["issue"])))
    if metadata.get("pages"):
        fields.append(("pages", str(metadata["pages"])))
    if metadata.get("doi"):
        fields.append(("doi", str(metadata["doi"])))
    if metadata.get("url"):
        fields.append(("url", _bibtex_brace(str(metadata["url"]))))
    if metadata.get("publisher") and typ == "book":
        fields.append(("publisher", _bibtex_brace(str(metadata["publisher"]))))
    if metadata.get("isbn"):
        fields.append(("isbn", str(metadata["isbn"])))
    lines = [f"@{typ}{{{key},"]
    for name, val in fields:
        lines.append(f"  {name} = {{{val}}},")
    lines.append("}")
    return "\n".join(lines)


def _bibtex_brace(s: str) -> str:
    return str(s).replace("{", "\\{").replace("}", "\\}")


def _bibtex_cite_key(meta: dict[str, Any]) -> str:
    authors = normalize_authors(meta.get("authors") or [])
    last = (authors[0].get("last") or "unknown").lower()
    last = re.sub(r"\W+", "", last) or "unknown"
    year = meta.get("year") or "nd"
    title = meta.get("title") or ""
    token = re.sub(r"\W+", "", title[:20].lower()) or "item"
    return f"{last}{year}{token}"


def _guess_bibtex_type(meta: dict[str, Any]) -> str:
    st = (meta.get("source_type") or "").lower()
    if st == "book":
        return "book"
    if st in ("web", "webpage"):
        return "misc"
    return "article"


def export_ris(metadata: dict[str, Any]) -> str:
    """
    Exporte une référence au format RIS.

    Args:
        metadata: Métadonnées normalisées.

    Returns:
        Contenu d'un fichier .ris (une entrée TY  - ER).
    """
    lines: list[str] = []
    typ = metadata.get("source_type") or "article"
    ris_ty = "BOOK" if typ == "book" else "JOUR" if typ == "article" else "ELEC"
    lines.append(f"TY  - {ris_ty}")
    title = metadata.get("title")
    if title:
        lines.append(f"TI  - {title}")
    for a in normalize_authors(metadata.get("authors") or []):
        name = f"{a.get('last', '')}, {a.get('first', '')}".strip(", ")
        if name:
            lines.append(f"AU  - {name}")
    if metadata.get("year"):
        lines.append(f"PY  - {metadata['year']}")
    if metadata.get("journal"):
        lines.append(f"JO  - {metadata['journal']}")
    if metadata.get("volume"):
        lines.append(f"VL  - {metadata['volume']}")
    if metadata.get("issue"):
        lines.append(f"IS  - {metadata['issue']}")
    if metadata.get("pages"):
        lines.append(f"SP  - {metadata['pages']}")
    if metadata.get("doi"):
        lines.append(f"DO  - {metadata['doi']}")
    if metadata.get("url"):
        lines.append(f"UR  - {metadata['url']}")
    if metadata.get("publisher"):
        lines.append(f"PB  - {metadata['publisher']}")
    if metadata.get("isbn"):
        lines.append(f"SN  - {metadata['isbn']}")
    lines.append("ER  - ")
    return "\n".join(lines) + "\n"


def export_markdown(metadata: dict[str, Any], citation_text: str) -> str:
    """
    Formate une entrée Markdown pour bibliographie.

    Args:
        metadata: Métadonnées (pour titre optionnel en entête).
        citation_text: Ligne de citation déjà formatée.

    Returns:
        Bloc Markdown.
    """
    title = metadata.get("title") or ""
    header = f"## {title}\n\n" if title else ""
    return f"{header}{citation_text}\n"


def export_html(citation_text: str) -> str:
    """
    Encapsule une citation en HTML sûr (échappement basique).

    Args:
        citation_text: Texte brut de la citation.

    Returns:
        Fragment HTML <p>.
    """
    import html

    return f"<p>{html.escape(citation_text)}</p>\n"


def extract_arxiv_id_from_url(url: str) -> str | None:
    """Extrait l'identifiant arXiv depuis une URL abs ou pdf."""
    m = _ARXIV_ABS.search(url)
    return m.group("id") if m else None


def clean_doi(doi: str) -> str:
    """Retire le préfixe https://doi.org/ d'un DOI si présent."""
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.I).strip()


async def fetch_semantic_scholar_by_doi(
    doi: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any] | None:
    """
    Récupère des métadonnées via l'API Semantic Scholar (gratuite, sans clé).

    Args:
        doi: DOI nettoyé.
        client: Client httpx async réutilisable.

    Returns:
        Dict normalisé ou None si échec.
    """
    from urllib.parse import quote

    doi = clean_doi(doi)
    encoded = quote(doi, safe="")
    api_url = (
        "https://api.semanticscholar.org/graph/v1/paper/DOI:"
        f"{encoded}?fields=title,authors,year,venue,publicationVenue,externalIds,url"
    )

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        close_client = True
    try:
        r = await client.get(api_url)
        if r.status_code != 200:
            return None
        data = r.json()
        return _normalize_semantic_paper(data)
    finally:
        if close_client:
            await client.aclose()


async def fetch_semantic_scholar_by_title(
    title: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any] | None:
    """
    Recherche un article par titre sur Semantic Scholar.

    Args:
        title: Titre approximatif.
        client: Client httpx optionnel.

    Returns:
        Dict normalisé du premier résultat ou None.
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        close_client = True
    try:
        r = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": title.strip(),
                "limit": 1,
                "fields": (
                    "title,authors,year,venue,publicationVenue,externalIds,url"
                ),
            },
        )
        if r.status_code != 200:
            return None
        payload = r.json()
        hits = payload.get("data") or []
        if not hits:
            return None
        return _normalize_semantic_paper(hits[0])
    finally:
        if close_client:
            await client.aclose()


def _normalize_semantic_paper(data: dict[str, Any]) -> dict[str, Any]:
    """Convertit une réponse Semantic Scholar en schéma interne."""
    authors_raw: list[dict[str, str]] = []
    for au in data.get("authors") or []:
        name = au.get("name") or ""
        if name:
            authors_raw.append({"name": name})
    ext = data.get("externalIds") or {}
    doi = ext.get("DOI") or ""
    venue = data.get("venue") or ""
    if not venue and data.get("publicationVenue"):
        pv = data["publicationVenue"]
        if isinstance(pv, dict):
            venue = pv.get("name") or ""
    meta: dict[str, Any] = {
        "title": data.get("title") or "",
        "authors": authors_raw,
        "year": data.get("year"),
        "journal": venue or "",
        "volume": "",
        "issue": "",
        "pages": "",
        "doi": doi,
        "url": data.get("url") or (f"https://doi.org/{doi}" if doi else ""),
        "publisher": "",
        "source_type": "article",
    }
    return meta


def suggest_style(metadata: dict[str, Any]) -> str:
    """
    Propose un style de citation selon des heuristiques sur le domaine.

    Args:
        metadata: Métadonnées (journal, titre, concepts éventuels).

    Returns:
        Nom de style : Vancouver, IEEE, APA ou Chicago.
    """
    blob = " ".join(
        str(metadata.get(k, "") or "").lower()
        for k in ("journal", "title", "publisher", "venue")
    )
    medical = (
        "lancet",
        "nejm",
        "jama",
        "bmj",
        "nature medicine",
        "clinical",
        "medical",
        "health",
        "patient",
        "hospital",
    )
    cs = (
        "ieee",
        "computer",
        "software",
        "algorithm",
        "neural",
        "learning",
        "arxiv",
        "proceedings of",
        "conference on",
    )
    social = (
        "sociology",
        "psychology",
        "anthropology",
        "political",
        "education",
        "review",
    )
    for kw in medical:
        if kw in blob:
            return "Vancouver"
    for kw in cs:
        if kw in blob:
            return "IEEE"
    for kw in social:
        if kw in blob:
            return "APA"
    return "APA"
