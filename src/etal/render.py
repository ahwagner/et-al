"""Pure formatting for the reports: tables, CSV, the NLM citation, and the presentation line."""
from __future__ import annotations

import csv
import io

from etal.dates import PartialDate
from etal.schema import Person, Presentation, Publication

__all__ = ["FORMAT_LABELS", "format_label", "date_prefix", "markdown_table", "csv_text", "nlm_citation", "presentation_line"]

FORMAT_LABELS = {
    "poster": "Poster",
    "invited talk": "Invited talk",
    "platform": "Podium presentation",
    "lightning talk": "Lightning talk",
    "workshop": "Workshop session",
    "panel": "Panel discussion",
    "course lecture": "Course lecture",
    "hackathon": "Hackathon",
    "consortium update": "Consortium update",
    "other": "Presentation",
}


def format_label(fmt: str) -> str:
    return FORMAT_LABELS.get(fmt, FORMAT_LABELS["other"])


def date_prefix(d: PartialDate) -> str:
    return str(d)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    def line(cells: list[str]) -> str:
        return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |\n"

    return line(headers) + line(["---"] * len(headers)) + "".join(line(row) for row in rows)


def csv_text(headers: list[str], rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue()


def _sentence(text: str) -> str:
    """End text with a period unless it already ends in sentence punctuation."""
    return text if text.endswith((".", "?", "!")) else f"{text}."


def nlm_citation(pub: Publication) -> str:
    parts: list[str] = []
    if pub.authors:
        parts.append(", ".join(pub.authors) + ".")
    if pub.title:
        parts.append(_sentence(pub.title))
    if pub.journal is not None and pub.journal.abbreviation:
        parts.append(f"{pub.journal.abbreviation}.")
    if pub.date is not None:
        where = ""
        if pub.volume:
            where = f";{pub.volume}" + (f"({pub.issue})" if pub.issue else "") + (f":{pub.pages}" if pub.pages else "")
        elif pub.pages:
            where = f";{pub.pages}"
        parts.append(f"{pub.date.year}{where}.")
    if pub.doi:
        parts.append(f"https://doi.org/{pub.doi}.")
    ids = [f"PMID: {pub.pmid}" if pub.pmid else "", f"PMCID: {pub.pmcid}" if pub.pmcid else ""]
    ids = [i for i in ids if i]
    if ids:
        parts.append("; ".join(ids) + ".")
    return " ".join(parts)


def presentation_line(p: Presentation) -> str:
    head = f"{format_label(p.format or 'other')}, {p.attendance or ''}".rstrip(", ")
    names = [x.name if isinstance(x, Person) else x for x in p.presenters]
    parts: list[str] = []
    if names:
        parts.append(", ".join(names) + ".")
    if p.title:
        parts.append(_sentence(p.title))
    where = ", ".join(x for x in (p.event.name if p.event is not None else None, p.location) if x)
    if where:
        parts.append(f"{where}.")
    if p.audience:
        parts.append(f"{p.audience[0].upper()}{p.audience[1:]}.")
    if not (p.date is not None and p.date.day_recorded):
        parts.append("Day not recorded.")
    return f"{head} | {' '.join(parts)}"
