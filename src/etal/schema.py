"""Record types for every note type, loading with link resolution, and validation."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from etal.config import Config, parse_wikilink
from etal.dates import PartialDate
from etal.vault import Note, read_folder

__all__ = [
    "parse_wikilink", "Problem", "coerce_str", "load", "validate", "VaultData",
    "Journal", "Conference", "Person", "Award", "Publication", "Presentation", "Honor",
    "PUBLICATION_FORMATS", "PUBLICATION_STATUSES", "PRESENTATION_FORMATS",
    "ATTENDANCE", "AUDIENCES", "HONOR_RESULTS", "AWARD_ROLES",
]

PUBLICATION_FORMATS = ["article", "preprint", "review", "book chapter", "white paper", "dataset", "software", "abstract", "other"]
PUBLICATION_STATUSES = ["published", "accepted", "submitted", "preprint", "in preparation"]
PRESENTATION_FORMATS = ["poster", "invited talk", "platform", "lightning talk", "workshop", "panel", "course lecture", "hackathon", "consortium update", "other"]
ATTENDANCE = ["in person", "virtual"]
AUDIENCES = ["international", "national", "regional", "institutional", "local"]
HONOR_RESULTS = ["won", "nominated", "finalist"]
AWARD_ROLES = ["PI", "contact PI", "MPI", "co-I", "OSC", "consultant"]

# Folder key in Config.folders -> the `type` its notes must carry.
FOLDER_TYPES = {
    "journals": "journal",
    "conferences": "conference",
    "people": "person",
    "awards": "award",
    "publications": "publication",
    "presentations": "presentation",
    "honors": "honor",
}


@dataclass(frozen=True, order=True)
class Problem:
    path: Path
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.field}: {self.message}"


def coerce_str(value: Any) -> str | None:
    """Text from a YAML scalar: ints become text, None and blank become None, text is stripped."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"expected text, got {value!r}")
    text = str(value).strip()
    return text or None


# Records. Link fields named *_link hold the property as written (a wikilink string); the
# fields beside them hold what it resolved to, or None when it did not resolve.
# eq=False keeps identity comparison, so a records graph with supersedes links cannot recurse.

@dataclass(eq=False)
class Journal:
    note: Note = field(repr=False)
    name: str | None
    abbreviation: str | None
    issn: str | None
    eissn: str | None
    publisher: str | None
    url: str | None
    peer_reviewed: bool | None
    nlm_id: str | None


@dataclass(eq=False)
class Conference:
    note: Note = field(repr=False)
    name: str | None
    series: str | None
    start: PartialDate | None
    end: PartialDate | None
    location: str | None
    audience: str | None
    organizer: str | None
    url: str | None
    attended: bool

    @property
    def effective_end(self) -> PartialDate | None:
        return self.end or self.start


@dataclass(eq=False)
class Person:
    note: Note = field(repr=False)
    name: str
    aliases: list[str]
    orcid: str | None
    scholar_id: str | None
    lab_member: bool
    tenure: list[dict]


@dataclass(eq=False)
class Award:
    note: Note = field(repr=False)
    name: str
    grant_number: str | None
    funder: str | None
    role: str | None
    start: PartialDate | None
    end: PartialDate | None


@dataclass(eq=False)
class Publication:
    note: Note = field(repr=False)
    title: str | None
    format: str | None
    status: str | None
    date: PartialDate | None
    journal_link: str | None
    journal: Journal | None = field(repr=False)
    volume: str | None
    issue: str | None
    pages: str | None
    authors: list[str]
    co_first: list[str]
    corresponding: list[str]
    senior: list[str]
    peer_reviewed_own: bool | None
    doi: str | None
    pmid: str | None
    pmcid: str | None
    url: str | None
    scholar_id: str | None
    citations: int | None
    citations_as_of: dt.date | None
    grant_links: list[str]
    grants: list[Award] = field(repr=False)
    supersedes_link: str | None
    supersedes: Publication | None = field(repr=False)
    stage: str | None
    sources: list[str]
    notes: str | None

    @property
    def peer_reviewed(self) -> bool:
        if self.peer_reviewed_own is not None:
            return self.peer_reviewed_own
        if self.journal is not None and self.journal.peer_reviewed is not None:
            return self.journal.peer_reviewed
        return False


@dataclass(eq=False)
class Presentation:
    note: Note = field(repr=False)
    title: str | None
    date: PartialDate | None
    format: str | None
    attendance: str | None
    event_link: str | None
    event: Conference | None = field(repr=False)
    session: str | None
    location_own: str | None
    audience_own: str | None
    presenter_links: list[str]
    presenters: list[Person | str] = field(repr=False)
    coauthors: list[str]
    grant_links: list[str]
    grants: list[Award] = field(repr=False)
    slides: str | None
    poster: str | None
    abstract_doi: str | None
    sources: list[str]
    notes: str | None

    @property
    def location(self) -> str | None:
        if self.location_own is not None:
            return self.location_own
        return self.event.location if self.event is not None else None

    @property
    def audience(self) -> str | None:
        if self.audience_own is not None:
            return self.audience_own
        return self.event.audience if self.event is not None else None


@dataclass(eq=False)
class Honor:
    note: Note = field(repr=False)
    name: str | None
    date: PartialDate | None
    result: str | None
    venue: str | None
    event_link: str | None
    event: Conference | None = field(repr=False)
    audience_own: str | None
    recipient_link: str | None
    recipient: Person | None = field(repr=False)
    related_link: str | None
    related: Publication | Presentation | None = field(repr=False)
    sources: list[str]
    notes: str | None

    @property
    def audience(self) -> str | None:
        if self.audience_own is not None:
            return self.audience_own
        return self.event.audience if self.event is not None else None


@dataclass
class VaultData:
    config: Config
    journals: list[Journal]
    conferences: list[Conference]
    people: list[Person]
    awards: list[Award]
    publications: list[Publication]
    presentations: list[Presentation]
    honors: list[Honor]
    problems: list[Problem]
    by_name: dict[str, dict[str, Any]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.by_name = {
            key: {r.note.name: r for r in records}
            for key, records in [
                ("journals", self.journals),
                ("conferences", self.conferences),
                ("people", self.people),
                ("awards", self.awards),
                ("publications", self.publications),
                ("presentations", self.presentations),
                ("honors", self.honors),
            ]
        }

    @property
    def people_by_name(self) -> dict[str, Person]:
        return self.by_name["people"]


class _Fields:
    """Typed reads of one note's frontmatter. A bad value becomes a Problem and reads as blank."""

    def __init__(self, note: Note, problems: list[Problem]) -> None:
        self.note = note
        self.problems = problems
        self.fm = note.frontmatter or {}

    def _bad(self, key: str, message: str) -> None:
        self.problems.append(Problem(self.note.path, key, message))

    def str(self, key: str) -> str | None:
        value = self.fm.get(key)
        if isinstance(value, list):
            self._bad(key, 'expected a single value, got a list (an unquoted [[link]] reads as a list; write "[[Name]]")')
            return None
        try:
            return coerce_str(value)
        except ValueError as exc:
            self._bad(key, str(exc))
            return None

    def bool(self, key: str) -> bool | None:
        value = self.fm.get(key)
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        self._bad(key, f"expected true or false, got {value!r}")
        return None

    def int(self, key: str) -> int | None:
        value = self.fm.get(key)
        if value is None or value == "":
            return None
        if isinstance(value, int) and not isinstance(value, bool):
            return int(value)
        self._bad(key, f"expected a whole number, got {value!r}")
        return None

    def partial_date(self, key: str) -> PartialDate | None:
        value = self.fm.get(key)
        if value is None or value == "":
            return None
        try:
            return PartialDate.parse(value)
        except ValueError:
            self._bad(key, f"expected YYYY, YYYY-MM, or YYYY-MM-DD, got {value!r}")
            return None

    def day(self, key: str) -> dt.date | None:
        value = self.fm.get(key)
        if value is None or value == "":
            return None
        try:
            if isinstance(value, dt.datetime):
                return value.date()
            if isinstance(value, dt.date):
                return dt.date(value.year, value.month, value.day)
            if isinstance(value, str):
                return dt.date.fromisoformat(value.strip())
        except ValueError:
            pass
        self._bad(key, f"expected a date as YYYY-MM-DD, got {value!r}")
        return None

    def strs(self, key: str) -> list[str]:
        value = self.fm.get(key)
        if value is None or value == "":
            return []
        if not isinstance(value, list):
            self._bad(key, f"expected a list, got {value!r}")
            return []
        out: list[str] = []
        for item in value:
            try:
                text = coerce_str(item)
            except ValueError as exc:
                self._bad(key, str(exc))
                continue
            if text is None:
                self._bad(key, "empty entry in list")
                continue
            out.append(text)
        return out

    def tenure(self, key: str) -> list[dict]:
        value = self.fm.get(key)
        if value is None or value == "":
            return []
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            self._bad(key, "expected a list of mappings (start, end, role)")
            return []
        return [dict(item) for item in value]


def _journal(note: Note, f: _Fields) -> Journal:
    return Journal(
        note=note, name=f.str("name"), abbreviation=f.str("abbreviation"), issn=f.str("issn"),
        eissn=f.str("eissn"), publisher=f.str("publisher"), url=f.str("url"),
        peer_reviewed=f.bool("peer_reviewed"), nlm_id=f.str("nlm_id"),
    )


def _conference(note: Note, f: _Fields) -> Conference:
    return Conference(
        note=note, name=f.str("name"), series=f.str("series"), start=f.partial_date("start"),
        end=f.partial_date("end"), location=f.str("location"), audience=f.str("audience"),
        organizer=f.str("organizer"), url=f.str("url"), attended=bool(f.bool("attended")),
    )


def _person(note: Note, f: _Fields) -> Person:
    return Person(
        note=note, name=note.name, aliases=f.strs("aliases"), orcid=f.str("orcid"),
        scholar_id=f.str("scholar_id"), lab_member=bool(f.bool("lab_member")), tenure=f.tenure("tenure"),
    )


def _award(note: Note, f: _Fields) -> Award:
    return Award(
        note=note, name=note.name, grant_number=f.str("grant_number"), funder=f.str("funder"),
        role=f.str("role"), start=f.partial_date("start"), end=f.partial_date("end"),
    )


def _publication(note: Note, f: _Fields) -> Publication:
    return Publication(
        note=note, title=f.str("title"), format=f.str("format"), status=f.str("status"),
        date=f.partial_date("date"), journal_link=f.str("journal"), journal=None,
        volume=f.str("volume"), issue=f.str("issue"), pages=f.str("pages"),
        authors=f.strs("authors"), co_first=f.strs("co_first"), corresponding=f.strs("corresponding"),
        senior=f.strs("senior"), peer_reviewed_own=f.bool("peer_reviewed"), doi=f.str("doi"),
        pmid=f.str("pmid"), pmcid=f.str("pmcid"), url=f.str("url"), scholar_id=f.str("scholar_id"),
        citations=f.int("citations"), citations_as_of=f.day("citations_as_of"),
        grant_links=f.strs("grants"), grants=[], supersedes_link=f.str("supersedes"), supersedes=None,
        stage=f.str("stage"), sources=f.strs("sources"), notes=f.str("notes"),
    )


def _presentation(note: Note, f: _Fields) -> Presentation:
    return Presentation(
        note=note, title=f.str("title"), date=f.partial_date("date"), format=f.str("format"),
        attendance=f.str("attendance"), event_link=f.str("event"), event=None, session=f.str("session"),
        location_own=f.str("location"), audience_own=f.str("audience"),
        presenter_links=f.strs("presenters"), presenters=[], coauthors=f.strs("coauthors"),
        grant_links=f.strs("grants"), grants=[], slides=f.str("slides"), poster=f.str("poster"),
        abstract_doi=f.str("abstract_doi"), sources=f.strs("sources"), notes=f.str("notes"),
    )


def _honor(note: Note, f: _Fields) -> Honor:
    return Honor(
        note=note, name=f.str("name"), date=f.partial_date("date"), result=f.str("result"),
        venue=f.str("venue"), event_link=f.str("event"), event=None, audience_own=f.str("audience"),
        recipient_link=f.str("recipient"), recipient=None, related_link=f.str("related"), related=None,
        sources=f.strs("sources"), notes=f.str("notes"),
    )


_BUILDERS: dict[str, Callable[[Note, _Fields], Any]] = {
    "journals": _journal,
    "conferences": _conference,
    "people": _person,
    "awards": _award,
    "publications": _publication,
    "presentations": _presentation,
    "honors": _honor,
}


def _type_problem(note: Note, expected: str, key: str) -> str | None:
    if note.parse_error is not None:
        return f"cannot read frontmatter: {note.parse_error}"
    if key == "people":
        # People notes are typed by their folder: no frontmatter or no `type` is fine.
        actual = note.frontmatter.get("type") if note.frontmatter is not None else None
        if actual is None or actual == "" or actual == expected:
            return None
        return f"is '{actual}' but this folder holds '{expected}'"
    if note.frontmatter is None:
        return f"no frontmatter; expected type: {expected}"
    actual = note.frontmatter.get("type")
    if actual is None or actual == "":
        return f"missing; expected type: {expected}"
    if actual != expected:
        return f"is '{actual}' but this folder holds '{expected}'"
    return None


class _Resolver:
    def __init__(self, config: Config, by_name: dict[str, dict[str, Any]], problems: list[Problem]) -> None:
        self.config = config
        self.by_name = by_name
        self.problems = problems

    def one(self, note: Note, field_name: str, link: str | None, *keys: str) -> Any:
        """Resolve a wikilink against one or more folders, in order."""
        if link is None:
            return None
        name = parse_wikilink(link)
        if name is None:
            self.problems.append(Problem(note.path, field_name, f"expected a wikilink such as [[Name]], got {link!r}"))
            return None
        for key in keys:
            record = self.by_name[key].get(name)
            if record is not None:
                return record
        where = " or ".join(self.config.folders[key] for key in keys)
        self.problems.append(Problem(note.path, field_name, f"no note named '{name}' in {where}"))
        return None

    def many(self, note: Note, field_name: str, links: list[str], key: str) -> list[Any]:
        return [r for r in (self.one(note, field_name, link, key) for link in links) if r is not None]


def load(config: Config) -> VaultData:
    problems: list[Problem] = []
    records: dict[str, list[Any]] = {key: [] for key in FOLDER_TYPES}

    # Pass 1: one record per well-formed note, links kept as written.
    for key, expected in FOLDER_TYPES.items():
        for note in read_folder(config.folder(key)):
            message = _type_problem(note, expected, key)
            if message is not None:
                problems.append(Problem(note.path, "type", message))
                continue
            records[key].append(_BUILDERS[key](note, _Fields(note, problems)))

    data = VaultData(
        config=config, journals=records["journals"], conferences=records["conferences"],
        people=records["people"], awards=records["awards"], publications=records["publications"],
        presentations=records["presentations"], honors=records["honors"], problems=problems,
    )

    # Pass 2: resolve links across folders.
    resolve = _Resolver(config, data.by_name, problems)
    for pub in data.publications:
        pub.journal = resolve.one(pub.note, "journal", pub.journal_link, "journals")
        pub.grants = resolve.many(pub.note, "grants", pub.grant_links, "awards")
        pub.supersedes = resolve.one(pub.note, "supersedes", pub.supersedes_link, "publications")
    for pres in data.presentations:
        pres.event = resolve.one(pres.note, "event", pres.event_link, "conferences")
        pres.grants = resolve.many(pres.note, "grants", pres.grant_links, "awards")
        for link in pres.presenter_links:
            if parse_wikilink(link) is None:
                pres.presenters.append(link)  # a plain name for someone outside the lab
                continue
            person = resolve.one(pres.note, "presenters", link, "people")
            pres.presenters.append(person if person is not None else parse_wikilink(link))
    for honor in data.honors:
        honor.event = resolve.one(honor.note, "event", honor.event_link, "conferences")
        honor.recipient = resolve.one(honor.note, "recipient", honor.recipient_link, "people")
        honor.related = resolve.one(honor.note, "related", honor.related_link, "publications", "presentations")
    return data


def _missing(out: list[Problem], record: Any, key: str, present: bool) -> None:
    if not present:
        out.append(Problem(record.note.path, key, "required"))


def _enum(out: list[Problem], record: Any, key: str, value: str | None, allowed: list[str]) -> None:
    """A set value must be one of `allowed`. A missing value is the required check's business."""
    if value is not None and value not in allowed:
        out.append(Problem(record.note.path, key, f"must be one of: {' | '.join(allowed)}"))


def _duplicates(out: list[Problem], items: list[tuple[Any, str, str | None]]) -> None:
    """Report every (record, key) whose value is also held by a different record."""
    holders: dict[str, list[tuple[Any, str]]] = {}
    for record, key, value in items:
        if value is not None:
            holders.setdefault(value.casefold(), []).append((record, key))
    for group in holders.values():
        if len({id(record) for record, _ in group}) < 2:
            continue
        for record, key in group:
            others = sorted({r.note.name for r, _ in group if r is not record})
            out.append(Problem(record.note.path, key, f"also used by: {', '.join(others)}"))


def _validate_journals(data: VaultData, out: list[Problem]) -> None:
    for j in data.journals:
        _missing(out, j, "name", j.name is not None)
        _missing(out, j, "abbreviation", j.abbreviation is not None)
        _missing(out, j, "peer_reviewed", j.peer_reviewed is not None)
    _duplicates(out, [(j, key, getattr(j, key)) for j in data.journals for key in ("issn", "eissn")])


def _validate_conferences(data: VaultData, out: list[Problem]) -> None:
    for c in data.conferences:
        _missing(out, c, "name", c.name is not None)
        _missing(out, c, "start", c.start is not None)
        _missing(out, c, "location", c.location is not None)
        _missing(out, c, "audience", c.audience is not None)
        _enum(out, c, "audience", c.audience, AUDIENCES)


def _validate_publications(data: VaultData, out: list[Problem], ambiguous: Callable[[Any, str, list[str]], None]) -> None:
    for pub in data.publications:
        _missing(out, pub, "title", pub.title is not None)
        _missing(out, pub, "format", pub.format is not None)
        _missing(out, pub, "status", pub.status is not None)
        _missing(out, pub, "date", pub.date is not None)
        _missing(out, pub, "authors", bool(pub.authors))
        _missing(out, pub, "journal", pub.journal_link is not None)
        _enum(out, pub, "format", pub.format, PUBLICATION_FORMATS)
        _enum(out, pub, "status", pub.status, PUBLICATION_STATUSES)
        _enum(out, pub, "stage", pub.stage, data.config.stage_names)
        for key in ("authors", "co_first", "corresponding", "senior"):
            ambiguous(pub, key, getattr(pub, key))
    for key in ("doi", "pmid", "scholar_id"):
        _duplicates(out, [(pub, key, getattr(pub, key)) for pub in data.publications])


def _validate_presentations(data: VaultData, out: list[Problem], ambiguous: Callable[[Any, str, list[str]], None]) -> None:
    for pres in data.presentations:
        # A hackathon or workshop may carry a blank title, but the property must still be there.
        blank_ok = pres.format in ("hackathon", "workshop") and "title" in (pres.note.frontmatter or {})
        _missing(out, pres, "title", pres.title is not None or blank_ok)
        _missing(out, pres, "date", pres.date is not None)
        _missing(out, pres, "format", pres.format is not None)
        _missing(out, pres, "attendance", pres.attendance is not None)
        _missing(out, pres, "event", pres.event_link is not None)
        _missing(out, pres, "presenters", bool(pres.presenter_links))
        _enum(out, pres, "format", pres.format, PRESENTATION_FORMATS)
        _enum(out, pres, "attendance", pres.attendance, ATTENDANCE)
        _enum(out, pres, "audience", pres.audience_own, AUDIENCES)
        event = pres.event
        if pres.date is not None and event is not None and event.start is not None and event.effective_end is not None:
            if pres.date.first_day() < event.start.first_day() or pres.date.last_day() > event.effective_end.last_day():
                span = str(event.start) if event.effective_end == event.start else f"{event.start} to {event.effective_end}"
                out.append(Problem(pres.note.path, "date", f"{pres.date} is outside {event.note.name} ({span})"))
        ambiguous(pres, "coauthors", pres.coauthors)
        ambiguous(pres, "presenters", [p for p in pres.presenters if isinstance(p, str)])


def _validate_honors(data: VaultData, out: list[Problem]) -> None:
    for honor in data.honors:
        _missing(out, honor, "name", honor.name is not None)
        _missing(out, honor, "date", honor.date is not None)
        _missing(out, honor, "result", honor.result is not None)
        _missing(out, honor, "recipient", honor.recipient_link is not None)
        _enum(out, honor, "result", honor.result, HONOR_RESULTS)
        _enum(out, honor, "audience", honor.audience_own, AUDIENCES)


def validate(data: VaultData) -> list[Problem]:
    """Every problem in the vault, sorted: load-time problems plus the rule checks below."""
    from etal.people import AliasIndex  # people imports this module, so import late

    out = list(data.problems)
    index = AliasIndex.build(data.people)

    def ambiguous(record: Any, key: str, names: list[str]) -> None:
        for name in names:
            found = index.candidates(name)
            if len(found) > 1:
                who = ", ".join(sorted(p.note.name for p in found))
                out.append(Problem(record.note.path, key, f"'{name}' matches more than one person: {who}"))

    _validate_journals(data, out)
    _validate_conferences(data, out)
    for award in data.awards:
        _enum(out, award, "role", award.role, AWARD_ROLES)
    _validate_publications(data, out, ambiguous)
    _validate_presentations(data, out, ambiguous)
    _validate_honors(data, out)
    return sorted(set(out))
