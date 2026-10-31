"""The citation report: publications by career stage with citation counts and authorship flags."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from etal.people import AliasIndex, author_flags, is_author
from etal.render import csv_text, markdown_table
from etal.schema import PUBLICATION_FORMATS, Publication, VaultData

__all__ = ["Row", "Totals", "StageSection", "CitationReport", "build", "render_markdown", "render_csv"]

DEFAULT_STATUSES = {"published", "accepted"}
HEADERS = [
    "Title", "Date", "Journal", "Citations", "First / co-first", "Senior / Corresponding",
    "Peer Reviewed", "First or Corresponding and Peer Reviewed",
]


@dataclass
class Row:
    title: str
    date: str
    journal: str
    citations: int | None
    first: bool
    senior: bool
    peer_reviewed: bool
    first_or_corresponding_pr: bool


@dataclass
class Totals:
    count: int
    citations: int
    first: int
    senior: int


@dataclass
class StageSection:
    name: str
    rows: list[Row]
    totals: Totals


@dataclass
class CitationReport:
    person: str
    stages: list[StageSection]
    grand: Totals
    fcpr_count: int
    fcpr_citations: int
    oldest_as_of: dt.date | None


def _totals(rows: list[Row]) -> Totals:
    return Totals(
        count=len(rows),
        citations=sum(r.citations or 0 for r in rows),
        first=sum(r.first for r in rows),
        senior=sum(r.senior for r in rows),
    )


def _predecessors(pub: Publication) -> list[Publication]:
    """The notes pub supersedes, nearest first, to the end of the chain.

    A chain that loops back to pub has no head, so it folds nothing; validate reports the loop.
    """
    chain: list[Publication] = []
    seen = {id(pub)}
    prev = pub.supersedes
    while prev is not None and id(prev) not in seen:
        chain.append(prev)
        seen.add(id(prev))
        prev = prev.supersedes
    return [] if prev is pub else chain


def build(
    data: VaultData,
    person_name: str | None = None,
    formats: set[str] | None = None,
    statuses: set[str] | None = None,
) -> CitationReport:
    config = data.config
    name = person_name or config.self_name
    index = AliasIndex.build(data.people)
    person = data.people_by_name.get(name) or index.resolve(name)
    if person is None:
        raise ValueError(f"no person named {name!r} in the vault")
    if formats is None:
        formats = set(PUBLICATION_FORMATS) - {"abstract"}
    if statuses is None:
        statuses = DEFAULT_STATUSES

    selected = [
        p for p in data.publications
        if p.format in formats and p.status in statuses and is_author(p, person, index)
    ]

    # Fold every note a selected note supersedes, down the whole chain, into it. A predecessor folds in
    # whatever its own status, format, or authors; it is the same work. A selected note that another
    # selected note supersedes is counted only inside that one.
    extra: dict[int, int] = {}
    as_ofs: list[dt.date] = []
    if config.merge_superseded:
        chains = {id(pub): _predecessors(pub) for pub in selected}
        absorbed = {id(prev) for chain in chains.values() for prev in chain}
        selected = [pub for pub in selected if id(pub) not in absorbed]
        folded: set[int] = set()   # a note two others both claim to supersede still counts once
        for pub in selected:
            for prev in chains[id(pub)]:
                if id(prev) in folded:
                    continue
                folded.add(id(prev))
                extra[id(pub)] = extra.get(id(pub), 0) + (prev.citations or 0)
                if prev.citations_as_of is not None:
                    as_ofs.append(prev.citations_as_of)

    placed: dict[str, list[tuple[tuple, Row]]] = {stage: [] for stage in config.stage_names}
    fcpr_citations = 0
    fcpr_count = 0
    for pub in selected:
        flags = author_flags(pub, person, index)
        total = pub.citations
        if id(pub) in extra:
            total = (total or 0) + extra[id(pub)]
        stage = pub.stage or config.stage_for(pub.date)
        journal = ""
        if pub.journal is not None:
            journal = pub.journal.abbreviation or pub.journal.name or ""
        row = Row(
            title=pub.title or pub.note.name,
            date=str(pub.date) if pub.date is not None else "",
            journal=journal,
            citations=total,
            first=flags.first,
            senior=flags.senior_or_corresponding,
            peer_reviewed=flags.peer_reviewed,
            first_or_corresponding_pr=flags.first_or_corresponding_peer_reviewed,
        )
        key = (pub.date.first_day() if pub.date is not None else dt.date.min, row.title)
        placed.setdefault(stage, []).append((key, row))
        if pub.citations_as_of is not None:
            as_ofs.append(pub.citations_as_of)
        if row.first_or_corresponding_pr:
            fcpr_count += 1
            fcpr_citations += total or 0

    stages = []
    for stage_name, items in placed.items():
        rows = [row for _, row in sorted(items, key=lambda item: item[0])]
        stages.append(StageSection(stage_name, rows, _totals(rows)))
    all_rows = [row for s in stages for row in s.rows]
    return CitationReport(
        person=name,
        stages=stages,
        grand=_totals(all_rows),
        fcpr_count=fcpr_count,
        fcpr_citations=fcpr_citations,
        oldest_as_of=min(as_ofs) if as_ofs else None,
    )


def _yes(flag: bool) -> str:
    return "Yes" if flag else "No"


def _count(value: int | None) -> str:
    return "" if value is None else str(value)


def _sentence(t: Totals) -> str:
    return f"{t.count} papers, {t.citations} citations, {t.first} first or co-first, {t.senior} senior or corresponding."


def render_markdown(report: CitationReport, as_of: bool = False) -> str:
    parts = [f"# Citation report for {report.person}\n"]
    for stage in report.stages:
        rows = [
            [r.title, r.date, r.journal, _count(r.citations), _yes(r.first), _yes(r.senior),
             _yes(r.peer_reviewed), "TRUE" if r.first_or_corresponding_pr else "FALSE"]
            for r in stage.rows
        ]
        parts.append(f"\n## {stage.name}\n\n{markdown_table(HEADERS, rows)}\nTotal: {_sentence(stage.totals)}\n")
    parts.append(
        f"\n## Grand Total\n\nTotal: {_sentence(report.grand)}\n"
        f"\nFirst or Corresponding Peer Reviewed Total: {report.fcpr_count} papers, {report.fcpr_citations} citations.\n"
    )
    if as_of and report.oldest_as_of is not None:
        parts.append(f"\nCounts as of {report.oldest_as_of} (oldest citations_as_of in the set).\n")
    return "".join(parts)


def render_csv(report: CitationReport) -> str:
    headers = ["Stage", *HEADERS]
    rows: list[list[str]] = []
    for stage in report.stages:
        for r in stage.rows:
            rows.append([
                stage.name, r.title, r.date, r.journal, _count(r.citations), _yes(r.first), _yes(r.senior),
                _yes(r.peer_reviewed), "TRUE" if r.first_or_corresponding_pr else "FALSE",
            ])
        t = stage.totals
        rows.append([stage.name, "Total", str(t.count), "", str(t.citations), str(t.first), str(t.senior), "", ""])
    g = report.grand
    rows.append(["", "Grand Total", str(g.count), "", str(g.citations), str(g.first), str(g.senior), "", ""])
    rows.append(["", "First or Corresponding Peer Reviewed Total", str(report.fcpr_count), "", str(report.fcpr_citations), "", "", "", ""])
    return csv_text(headers, rows)
