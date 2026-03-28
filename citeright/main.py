"""Point d'entrée CLI cite-right (Typer + Rich + httpx async)."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Literal

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from citeright import __version__
from citeright.fetchers.arxiv import fetch_arxiv
from citeright.fetchers.books import fetch_by_isbn
from citeright.fetchers.crossref import fetch_by_doi
from citeright.fetchers.openalex import fetch_by_title
from citeright.formatters import STYLE_FORMATTERS
from citeright.formatters.ieee import format_ieee
from citeright.formatters.vancouver import format_vancouver
from citeright.utils import (
    HTTP_TIMEOUT,
    cache_get,
    cache_set,
    clean_doi,
    copy_to_clipboard,
    detect_input_type,
    export_bibtex,
    export_html,
    export_markdown,
    export_ris,
    extract_arxiv_id_from_url,
    fetch_semantic_scholar_by_doi,
    fetch_semantic_scholar_by_title,
    normalize_isbn_digits,
    suggest_style,
    validate_doi,
    validate_isbn,
)

app = typer.Typer(
    name="cite-right",
    add_completion=False,
    help="Citations académiques à partir d'un DOI, URL, ISBN ou titre (APIs gratuites).",
)
console = Console()

ExportFmt = Literal["text", "bibtex", "ris", "markdown", "html"]


def _doi_from_url(url: str) -> str | None:
    """Extrait un DOI d'une URL doi.org si présent."""
    if "doi.org/" in url.lower():
        part = url.split("doi.org/", 1)[1].split("?", 1)[0].strip().rstrip("/")
        return part or None
    return None


async def _resolve_metadata(
    source: str,
    kind: str,
    client: httpx.AsyncClient,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Récupère les métadonnées avec cache et chaîne de secours.

    Ordre : cache → API principale → fallbacks (OpenAlex / Semantic Scholar).
    """
    source = source.strip()
    cache_key = f"{kind}:{source}"

    if use_cache:
        hit = cache_get(cache_key)
        if hit is not None:
            return hit

    meta: dict[str, Any] | None = None
    err_note: str | None = None

    try:
        if kind == "doi":
            if not validate_doi(source):
                raise ValueError(
                    "Format DOI invalide (attendu : préfixe 10.xxxx/…). "
                    "Exemple : 10.1038/nature12345"
                )
            d = clean_doi(source)
            try:
                meta = await fetch_by_doi(d, client)
            except Exception as e1:
                err_note = str(e1)
                meta = await fetch_semantic_scholar_by_doi(d, client)
                if meta is None and err_note:
                    try:
                        meta = await fetch_by_title(d, client)
                    except Exception:
                        meta = None
        elif kind == "arxiv":
            aid = extract_arxiv_id_from_url(source) or source
            m = re.match(
                r"^(?:arxiv:)?(?P<id>\d{4}\.\d{4,5})(?:v\d+)?$",
                aid.strip(),
                re.I,
            )
            if m:
                aid = m.group("id")
            meta = await fetch_arxiv(aid, client)
        elif kind == "isbn":
            if not validate_isbn(source):
                raise ValueError(
                    "ISBN invalide (checksum). Vérifiez ISBN-10 ou ISBN-13."
                )
            isbn = normalize_isbn_digits(source)
            meta = await fetch_by_isbn(isbn, client)
        elif kind == "url":
            if "arxiv.org" in source.lower():
                aid = extract_arxiv_id_from_url(source)
                if aid:
                    meta = await fetch_arxiv(aid, client)
                else:
                    raise ValueError("Impossible d'extraire l'ID arXiv depuis cette URL.")
            else:
                doi_guess = _doi_from_url(source)
                if doi_guess and validate_doi(doi_guess):
                    meta = await _resolve_metadata(doi_guess, "doi", client, use_cache=False)
                else:
                    raise ValueError(
                        "URL non prise en charge directement. "
                        "Utilisez une URL arXiv, un lien doi.org, ou précisez --doi / --title."
                    )
        elif kind == "title":
            try:
                meta = await fetch_by_title(source, client)
            except Exception:
                meta = await fetch_semantic_scholar_by_title(source, client)
                if meta is None:
                    raise
        else:
            raise ValueError(f"Type de source inconnu : {kind}")
    except httpx.TimeoutException:
        raise ValueError(
            f"Délai dépassé ({int(HTTP_TIMEOUT)} s). Réessayez plus tard ou vérifiez le réseau."
        ) from None
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"Erreur HTTP {e.response.status_code} depuis l'API. "
            "Essayez avec --title ou un autre identifiant."
        ) from e

    if meta is None:
        raise ValueError(
            "Métadonnées introuvables. Essayez --title ou vérifiez le DOI / ISBN."
        )

    if use_cache:
        cache_set(cache_key, meta)
    return meta


def _format_citation(
    metadata: dict[str, Any],
    style: str,
    index: int = 1,
) -> str:
    """Applique le formatter de style (IEEE / Vancouver gèrent l'index)."""
    key = style.upper()
    if key not in STYLE_FORMATTERS:
        raise ValueError(f"Style inconnu : {style}. Styles : {', '.join(STYLE_FORMATTERS)}")
    if key == "IEEE":
        return format_ieee(metadata, index=index)
    if key == "VANCOUVER":
        return format_vancouver(metadata, index=index)
    fn = STYLE_FORMATTERS[key]
    return fn(metadata)


def _render_export(
    metadata: dict[str, Any],
    style: str,
    export: ExportFmt,
    index: int = 1,
) -> str:
    """Produit la sortie selon le format demandé."""
    if export == "bibtex":
        return export_bibtex(metadata, style=style)
    if export == "ris":
        return export_ris(metadata)
    if export == "markdown":
        text = _format_citation(metadata, style, index=index)
        return export_markdown(metadata, text)
    if export == "html":
        text = _format_citation(metadata, style, index=index)
        return export_html(text)
    return _format_citation(metadata, style, index=index)


def _run_interactive() -> None:
    """Mode guidé : saisie pas à pas."""
    console.print(Panel.fit("Mode [bold]interactif[/bold] cite-right", style="cyan"))
    raw = typer.prompt("Entrez un DOI, URL, ISBN ou titre")
    kind = detect_input_type(raw)
    console.print(f"Type détecté : [yellow]{kind}[/yellow]")
    style = typer.prompt(
        "Style (APA, MLA, IEEE, Chicago, Vancouver, Harvard)",
        default="APA",
    )
    export_s = typer.prompt(
        "Export (text, bibtex, ris, markdown, html)",
        default="text",
    )
    export_s = export_s.lower().strip()
    if export_s not in ("text", "bibtex", "ris", "markdown", "html"):
        export_s = "text"
    copy = typer.confirm("Copier dans le presse-papier ?", default=False)

    async def _go() -> tuple[dict[str, Any], str]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            with console.status("[bold green]Fetching metadata..."):
                meta = await _resolve_metadata(raw, kind, client)
            sug = suggest_style(meta)
            if typer.confirm(
                f"Style suggéré selon le domaine : [bold]{sug}[/bold]. L'utiliser ?",
                default=False,
            ):
                style_f = sug
            else:
                style_f = style.strip().upper()
            text = _render_export(
                meta,
                style_f,
                export=export_s,  # type: ignore[arg-type]
            )
            return meta, text

    try:
        metadata, text = asyncio.run(_go())
    except ValueError as e:
        console.print(Panel(str(e), title="Erreur", border_style="red"))
        raise typer.Exit(1) from e

    console.print(Panel(text, title="Citation", border_style="green"))
    if copy and copy_to_clipboard(text):
        console.print("[dim]Copié dans le presse-papier.[/dim]")


def _process_batch(
    path: Path,
    style: str,
    export: ExportFmt,
    output: Path | None,
    use_suggested: bool,
) -> None:
    """Traite un fichier (une source par ligne)."""
    lines = [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not lines:
        console.print("[red]Fichier vide ou sans lignes utiles.[/red]")
        raise typer.Exit(1)

    async def _fetch_all() -> list[tuple[str, str, dict[str, Any] | None, str | None]]:
        results: list[tuple[str, str, dict[str, Any] | None, str | None]] = []
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            for i, line in enumerate(lines, start=1):
                kind = detect_input_type(line)
                try:
                    meta = await _resolve_metadata(line, kind, client)
                    st = suggest_style(meta) if use_suggested else style.upper()
                    text = _render_export(meta, st, export=export, index=i)
                    results.append((line, kind, meta, text))
                except Exception as e:
                    results.append((line, kind, None, str(e)))
        return results

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching metadata...", total=1)
        rows = asyncio.run(_fetch_all())
        progress.update(task, completed=1)

    table = Table(title="Bibliographie (batch)")
    table.add_column("#", style="dim")
    table.add_column("Source")
    table.add_column("Type")
    table.add_column("Statut")
    table.add_column("Aperçu")

    for i, (line, kind, meta, text_or_err) in enumerate(rows, start=1):
        if meta is not None and text_or_err:
            status = "[green]OK[/green]"
            flat = text_or_err.replace("\n", " ")
            preview = flat if len(flat) <= 80 else flat[:80] + "…"
        else:
            status = f"[red]{text_or_err}[/red]"
            preview = "—"
        table.add_row(str(i), line[:40] + ("…" if len(line) > 40 else ""), kind, status, preview)

    console.print(table)

    ok_parts = [str(r[3]) for r in rows if r[2] is not None and r[3] is not None]
    body = "\n\n".join(ok_parts)

    if output:
        output.write_text(body, encoding="utf-8")
        console.print(f"[green]Écrit : {output}[/green]")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    query: str | None = typer.Argument(
        None,
        help="DOI, URL, ISBN ou titre (détection automatique du type).",
    ),
    doi: str | None = typer.Option(None, "--doi", help="Identifiant DOI"),
    url: str | None = typer.Option(None, "--url", help="URL (arXiv ou doi.org)"),
    title: str | None = typer.Option(None, "--title", help="Titre à rechercher (OpenAlex)"),
    isbn: str | None = typer.Option(None, "--isbn", help="ISBN-10 ou ISBN-13"),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        help="Fichier texte : une source par ligne",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Assistant interactif",
    ),
    style: str = typer.Option(
        "APA",
        "--style",
        "-s",
        help="APA, MLA, IEEE, Chicago, Vancouver, Harvard",
    ),
    use_suggested_style: bool = typer.Option(
        False,
        "--use-suggested-style",
        help="Applique le style recommandé selon le domaine (journal, titre…)",
    ),
    export: str = typer.Option(
        "text",
        "--export",
        "-e",
        help="text | bibtex | ris | markdown | html",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Fichier de sortie (.md, .html, .bib, .ris, etc.)",
    ),
    copy: bool = typer.Option(
        False,
        "--copy",
        "-c",
        help="Copier le résultat dans le presse-papier",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Afficher la version",
    ),
) -> None:
    """Génère des citations académiques à partir de métadonnées publiques."""
    if version:
        typer.echo(__version__)
        raise typer.Exit(0)

    if ctx.invoked_subcommand is not None:
        return

    export_l = export.lower().strip()
    if export_l not in ("text", "bibtex", "ris", "markdown", "html"):
        console.print(
            "[red]--export doit être : text, bibtex, ris, markdown ou html[/red]"
        )
        raise typer.Exit(1)
    export_fmt: ExportFmt = export_l  # type: ignore[assignment]

    if interactive:
        _run_interactive()
        return

    if batch is not None:
        if use_suggested_style:
            console.print(
                "[dim]--use-suggested-style : style suggéré par ligne selon les métadonnées.[/dim]"
            )
        _process_batch(batch, style, export_fmt, output, use_suggested_style)
        return

    # Source unique
    raw: str | None = None
    kind: str | None = None
    if doi:
        raw, kind = doi, "doi"
    elif url:
        raw, kind = url, "url"
    elif title:
        raw, kind = title, "title"
    elif isbn:
        raw, kind = isbn, "isbn"
    elif query:
        raw = query
        kind = detect_input_type(query)

    if not raw or not kind:
        console.print(ctx.get_help())
        console.print(
            Panel(
                "Indiquez une source : [bold]--doi[/bold], [bold]--url[/bold], "
                "[bold]--title[/bold], [bold]--isbn[/bold], un argument libre, "
                "ou [bold]--batch[/bold] / [bold]-i[/bold].",
                title="Aide rapide",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)

    async def _one() -> tuple[dict[str, Any], str]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            with console.status("[bold green]Fetching metadata..."):
                meta = await _resolve_metadata(raw, kind, client)  # type: ignore[arg-type]
            st_apply = suggest_style(meta) if use_suggested_style else style.upper()
            if use_suggested_style:
                console.print(
                    f"[dim]Style appliqué (suggéré) : [bold]{st_apply}[/bold][/dim]"
                )
            text = _render_export(meta, st_apply, export=export_fmt)
            return meta, text

    try:
        metadata, text = asyncio.run(_one())
    except ValueError as e:
        console.print(Panel(str(e), title="Erreur", border_style="red"))
        hint = "Essayez [bold]--title[/bold] « … » ou un autre identifiant."
        if kind == "doi":
            hint = "DOI introuvable. Essayez avec [bold]--title[/bold]."
        console.print(Panel(hint, border_style="yellow"))
        raise typer.Exit(1) from e

    console.print(Panel(text, title="Citation", border_style="green"))

    if output:
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]Fichier enregistré : {output}[/green]")

    if copy:
        if copy_to_clipboard(text):
            console.print("[bold cyan]Copié dans le presse-papier.[/bold cyan]")
        else:
            console.print(
                "[yellow]Impossible de copier (environnement sans presse-papier ?)[/yellow]"
            )


if __name__ == "__main__":
    app()
