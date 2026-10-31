"""Google Scholar citation sync.

Network access lives only in fetch(). match(), plan(), and only() are pure; apply() writes through
the vault module and does nothing at all when dry_run is set.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from etal.schema import Publication, VaultData
from etal.vault import append_csv_rows, read_csv_rows, write_frontmatter

HISTORY_HEADER = ["as_of", "note", "scholar_id", "citations"]


class FetchError(Exception):
    """The Scholar profile could not be read. Nothing has been written when this is raised."""


@dataclass(frozen=True)
class ScholarWork:
    scholar_id: str
    title: str
    year: int | None
    citations: int


@dataclass
class MatchResult:
    matched: list[tuple[Publication, ScholarWork]]
    unmatched_works: list[ScholarWork]
    unmatched_pubs: list[Publication]


@dataclass(frozen=True)
class Change:
    pub: Publication
    old: int | None
    new: int
    scholar_id_added: bool


def normalize_title(s: str) -> str:
    decomposed = unicodedata.normalize("NFKD", s)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[\W_]+", " ", stripped.casefold()).strip()


def fetch(profile_id: str) -> list[ScholarWork]:
    try:
        from scholarly import scholarly  # imported here so tests and --help never load it

        author = scholarly.search_author_id(profile_id)
        author = scholarly.fill(author, sections=["publications"])
        works = []
        for entry in author.get("publications", []):
            bib = entry.get("bib", {})
            year = bib.get("pub_year")
            works.append(ScholarWork(
                scholar_id=str(entry["author_pub_id"]),
                title=str(bib["title"]),
                year=int(year) if year not in (None, "") else None,
                citations=int(entry.get("num_citations") or 0),
            ))
        return works
    except Exception as exc:
        raise FetchError(str(exc)) from exc


def works_from_json(path: Path) -> list[ScholarWork]:
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        ScholarWork(
            scholar_id=str(item["scholar_id"]),
            title=str(item["title"]),
            year=item.get("year"),
            citations=int(item["citations"]),
        )
        for item in items
    ]


def match(works: list[ScholarWork], publications: list[Publication]) -> MatchResult:
    """Pair works with notes by scholar_id, then by normalized title. Each side matches at most once.

    A title shared by several unclaimed notes is ambiguous and is left unmatched rather than guessed.
    """
    pairs: dict[int, tuple[Publication, ScholarWork]] = {}
    free_works = list(works)

    by_id: dict[str, Publication] = {}
    for pub in publications:
        if pub.scholar_id and pub.scholar_id not in by_id:
            by_id[pub.scholar_id] = pub
    claimed: set[int] = set()
    rest: list[ScholarWork] = []
    for work in free_works:
        pub = by_id.get(work.scholar_id)
        if pub is not None and id(pub) not in claimed:
            claimed.add(id(pub))
            pairs[id(pub)] = (pub, work)
        else:
            rest.append(work)

    by_title: dict[str, list[Publication]] = {}
    for pub in publications:
        if id(pub) not in claimed and pub.title:
            by_title.setdefault(normalize_title(pub.title), []).append(pub)
    unmatched_works: list[ScholarWork] = []
    for work in rest:
        candidates = [p for p in by_title.get(normalize_title(work.title), []) if id(p) not in claimed]
        if len(candidates) == 1:
            claimed.add(id(candidates[0]))
            pairs[id(candidates[0])] = (candidates[0], work)
        else:
            unmatched_works.append(work)

    matched = sorted(pairs.values(), key=lambda pair: pair[0].note.name)
    unmatched_pubs = [p for p in publications if id(p) not in pairs]
    return MatchResult(matched, unmatched_works, unmatched_pubs)


def only(result: MatchResult, note_name: str) -> MatchResult:
    """Narrow a result to one note. Works with no note at all stay listed."""
    return MatchResult(
        [pair for pair in result.matched if pair[0].note.name == note_name],
        result.unmatched_works,
        [pub for pub in result.unmatched_pubs if pub.note.name == note_name],
    )


def plan(result: MatchResult, as_of: dt.date) -> list[Change]:
    changes = []
    for pub, work in result.matched:
        if pub.citations != work.citations or not pub.scholar_id:
            changes.append(Change(pub, pub.citations, work.citations, not pub.scholar_id))
    return changes


def apply(data: VaultData, result: MatchResult, as_of: dt.date, dry_run: bool) -> list[Change]:
    changes = plan(result, as_of)
    if dry_run:
        return changes
    entry = f"Google Scholar, {as_of.isoformat()}"
    rows = []
    for pub, work in result.matched:
        updates: dict[str, object] = {"citations": work.citations, "citations_as_of": as_of}
        if not pub.scholar_id:
            updates["scholar_id"] = work.scholar_id
        sources = [str(s) for s in (pub.note.frontmatter.get("sources") or [])]
        if not (sources and sources[-1].startswith("Google Scholar")):
            updates["sources"] = sources + [entry]
        write_frontmatter(pub.note, updates)
        rows.append([as_of.isoformat(), pub.note.name, pub.scholar_id or work.scholar_id, str(work.citations)])
    if rows:
        append_csv_rows(data.config.history_path, HISTORY_HEADER, rows)
    return changes


def last_sync_date(history_path: Path) -> dt.date | None:
    dates = []
    for row in read_csv_rows(history_path):
        try:
            dates.append(dt.date.fromisoformat(row["as_of"]))
        except (KeyError, ValueError):
            continue
    return max(dates) if dates else None
