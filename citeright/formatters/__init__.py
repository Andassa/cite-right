"""Formatage des citations par style."""

from citeright.formatters.apa import format_apa
from citeright.formatters.chicago import format_chicago
from citeright.formatters.harvard import format_harvard
from citeright.formatters.ieee import format_ieee
from citeright.formatters.mla import format_mla
from citeright.formatters.vancouver import format_vancouver

STYLE_FORMATTERS = {
    "APA": format_apa,
    "MLA": format_mla,
    "IEEE": format_ieee,
    "CHICAGO": format_chicago,
    "VANCOUVER": format_vancouver,
    "HARVARD": format_harvard,
}

__all__ = [
    "STYLE_FORMATTERS",
    "format_apa",
    "format_chicago",
    "format_harvard",
    "format_ieee",
    "format_mla",
    "format_vancouver",
]
