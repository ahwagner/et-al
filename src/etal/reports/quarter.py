"""The quarterly outputs note: papers, talks, honors, funding, and conferences for one quarter."""
from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass, field

from etal.dates import PartialDate
from etal.people import AliasIndex, is_author
from etal.render import format_label, nlm_citation, presentation_line
from etal.schema import Award, Conference, Honor, Presentation, Publication, VaultData
from etal.vault import exists, read_note

__all__ = ["Quarter", "QuarterNote", "in_window", "build", "render", "previous_note_text"]

_QUARTER = re.compile(r"^(\d{4})-Q([1-4])$")


@dataclass(frozen=True)
class Quarter:
    year: int
    q: int

    @classmethod
    def parse(cls, text: str) -> Quarter:
        match = _QUARTER.match(text.strip())
        if match is None:
            raise ValueError(f"{text!r} is not a quarter; write it like 2026-Q3")
        return cls(int(match.group(1)), int(match.group(2)))

    @property
    def start(self) -> dt.date:
        return dt.date(self.year, 3 * (self.q - 1) + 1, 1)

    @property
    def end(self) -> dt.date:
        month = 3 * self.q
        return dt.date(self.year, month, calendar.monthrange(self.year, month)[1])

    @property
    def label(self) -> str:
        return f"{self.year}-Q{self.q}"

    @property
    def previous(self) -> Quarter:
        return Quarter(self.year, self.q - 1) if self.q > 1 else Quarter(self.year - 1, 4)

    @property
    def month_names(self) -> str:
        return f"{calendar.month_name[self.start.month]} through {calendar.month_name[self.end.month]} {self.year}"


@dataclass
class QuarterNote:
    self_publications: list[Publication] = field(default_factory=list)
    accepted: list[Publication] = field(default_factory=list)
    lab_publications: list[Publication] = field(default_factory=list)
    self_presentations: list[Presentation] = field(default_factory=list)
    lab_presentations: list[Presentation] = field(default_factory=list)
    honors: list[Honor] = field(default_factory=list)
    funding: list[Award] = field(default_factory=list)
    conferences: list[tuple[Conference, list[Presentation]]] = field(default_factory=list)
    open_items: list[str] = field(default_factory=list)
    lookback_items: list[Publication | Presentation] = field(default_factory=list)
    lookback_months: list[dt.date] = field(default_factory=list)


def in_window(d: PartialDate, start: dt.date, end: dt.date) -> bool:
    return d.first_day() <= end and d.last_day() >= start


def _sorted(records: list, key=lambda r: r.date) -> list:
    return sorted(records, key=lambda r: (key(r), r.note.name))


def _self_person(data: VaultData, index: AliasIndex):
    return data.people_by_name.get(data.config.self_name) or index.resolve(data.config.self_name)


def _is_self_presenter(p: Presentation, me) -> bool:
    return me is not None and any(x is me for x in p.presenters)


def _lab_authored(pub: Publication, index: AliasIndex) -> bool:
    for name in pub.authors:
        person = index.resolve(name)
        if person is not None and person.lab_member:
            return True
    return False


def _place(data: VaultData, start: dt.date, end: dt.date):
    """Publications and presentations in [start, end], placed as the note places them."""
    index = AliasIndex.build(data.people)
    me = _self_person(data, index)
    pubs = [p for p in data.publications if p.date is not None and in_window(p.date, start, end)]
    mine = [p for p in pubs if me is not None and is_author(p, me, index)]
    published = [p for p in mine if p.status == "published"]
    accepted = [p for p in mine if p.status == "accepted"]
    lab = [p for p in pubs if p not in mine and _lab_authored(p, index)]
    talks = [p for p in data.presentations if p.date is not None and in_window(p.date, start, end)]
    own_talks = [p for p in talks if _is_self_presenter(p, me)]
    lab_talks = [p for p in talks if not _is_self_presenter(p, me)]
    return (_sorted(published), _sorted(accepted), _sorted(lab), _sorted(own_talks), _sorted(lab_talks))


def previous_note_text(data: VaultData, q: Quarter) -> str | None:
    path = data.config.folder("publications").parent / f"{q.previous.label} outputs.md"
    return read_note(path).body if exists(path) else None


def _shift_months(d: dt.date, months: int) -> dt.date:
    index = d.year * 12 + (d.month - 1) - months
    return dt.date(index // 12, index % 12 + 1, 1)


def _overlaps(c: Conference, start: dt.date, end: dt.date) -> bool:
    if c.start is None or c.effective_end is None:
        return False
    return c.start.first_day() <= end and c.effective_end.last_day() >= start


def _title(record: Publication | Presentation) -> str:
    return record.title or record.note.name


def build(data: VaultData, q: Quarter, lookback: int = 1) -> QuarterNote:
    if _self_person(data, AliasIndex.build(data.people)) is None:
        raise ValueError(f"no People note for {data.config.self_name!r}; the quarter note cannot tell your work from the lab's")
    published, accepted, lab, own_talks, lab_talks = _place(data, q.start, q.end)
    note = QuarterNote(
        self_publications=published,
        accepted=accepted,
        lab_publications=lab,
        self_presentations=own_talks,
        lab_presentations=lab_talks,
    )
    note.honors = _sorted([h for h in data.honors if h.date is not None and in_window(h.date, q.start, q.end)])
    note.funding = _sorted(
        [a for a in data.awards if a.start is not None and in_window(a.start, q.start, q.end)],
        key=lambda a: a.start,
    )
    attended = [c for c in data.conferences if c.attended and _overlaps(c, q.start, q.end)]
    for conf in _sorted(attended, key=lambda c: c.start):
        note.conferences.append((conf, [p for p in data.presentations if p.event is conf]))

    for pub in [*published, *accepted, *lab]:
        if not pub.date.day_recorded:
            note.open_items.append(f"{pub.note.name}: day not recorded")
    for talk in [*own_talks, *lab_talks]:
        if not talk.date.day_recorded:
            note.open_items.append(f"{talk.note.name}: day not recorded")
        for presenter in talk.presenters:
            if isinstance(presenter, str):
                note.open_items.append(f"{talk.note.name}: presenter '{presenter}' has no People note")
    for honor in data.honors:
        if honor.date is None:
            note.open_items.append(f"{honor.note.name}: no date recorded")
        elif not honor.date.day_recorded and in_window(honor.date, q.start, q.end):
            note.open_items.append(f"{honor.note.name}: day not recorded")

    if lookback > 0:
        first = _shift_months(q.start, lookback)
        note.lookback_months = [_shift_months(q.start, n) for n in range(lookback, 0, -1)]
        previous = previous_note_text(data, q)
        found = _place(data, first, q.start - dt.timedelta(days=1))
        items = sorted(
            [item for group in found for item in group],
            key=lambda r: (r.date, r.note.name),
        )
        note.lookback_items = [item for item in items if previous is None or _title(item) not in previous]
    return note


def _join_months(months: list[dt.date]) -> str:
    names = [calendar.month_name[m.month] for m in months]
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]


def _bullets(lines: list[str]) -> list[str]:
    return [f"- {line}" for line in lines] if lines else ["(none)"]


def _pub_lines(pubs: list[Publication]) -> list[str]:
    return [f"{p.date} | {nlm_citation(p)}" for p in pubs]


def _talk_lines(talks: list[Presentation]) -> list[str]:
    return [f"{t.date} | {presentation_line(t)}" for t in talks]


def _honor_line(h: Honor) -> str:
    who = h.recipient.name if h.recipient is not None else ""
    head = ". ".join(x for x in (who, ", ".join(y for y in (h.name, h.venue) if y)) if x)
    parts = [f"{head}." if head else ""]
    if h.audience:
        parts.append(f"{h.audience[0].upper()}{h.audience[1:]}.")
    if h.result:
        parts.append(f"{h.result[0].upper()}{h.result[1:]}.")
    if not h.date.day_recorded:
        parts.append("Day not recorded.")
    return f"{h.date} | " + " ".join(x for x in parts if x)


def _funding_line(a: Award) -> str:
    parts = [f"{x}." for x in (a.name, a.grant_number, a.funder) if x]
    if a.role:
        parts.append(f"{a.role[0].upper()}{a.role[1:]}.")
    return f"{a.start} | " + " ".join(parts)


def _conference_line(conf: Conference, talks: list[Presentation]) -> str:
    where = ", ".join(x for x in (conf.name, conf.location, f"{conf.start} to {conf.effective_end}") if x)
    labels: list[str] = []
    for talk in _sorted(talks):
        label = format_label(talk.format or "other")
        if label not in labels:
            labels.append(label)
    if labels:
        labels = [labels[0], *(x[0].lower() + x[1:] for x in labels[1:])]
    return f"{where}." + (f" {', '.join(labels)}." if labels else "")


def render(note: QuarterNote, q: Quarter, assembled: dt.date) -> str:
    months = note.lookback_months
    back = f", checked back to {_join_months(months)}" if months else ""
    out = [
        "---",
        "type: outputs",
        f"quarter: {q.label}",
        "kudos_due:",
        "kudos_submitted:",
        "---",
        f"# {q.label} outputs",
        "",
        f"Publications, presentations, and funding for {q.month_names}{back}. Drafted by etal on {assembled.isoformat()}.",
        "",
        "One note per quarter. Each line is written so it can be pasted into the form. "
        "Papers are placed by first online date, not issue date. Talks are placed by the date on the title slide.",
        "",
        "## Publications",
        "",
        *_bullets(_pub_lines(note.self_publications)),
        "",
        "Accepted, not yet published:",
        "",
        *_bullets(_pub_lines(note.accepted)),
        "",
        "Lab, without Alex as an author:",
        "",
        *_bullets(_pub_lines(note.lab_publications)),
        "",
    ]
    if months:
        lookback_lines = [
            f"{item.date} | " + (nlm_citation(item) if isinstance(item, Publication) else presentation_line(item))
            for item in note.lookback_items
        ]
        out += [f"## Checked back to {_join_months(months)}", "", *_bullets(lookback_lines), ""]
    out += [
        "## Presentations",
        "",
        "Alex:",
        "",
        *_bullets(_talk_lines(note.self_presentations)),
        "",
        "Lab:",
        "",
        *_bullets(_talk_lines(note.lab_presentations)),
        "",
        "## Honors",
        "",
        *_bullets([_honor_line(h) for h in note.honors]),
        "",
        "## Funding",
        "",
        *_bullets([_funding_line(a) for a in note.funding]),
        "",
        "## Conferences attended",
        "",
        *_bullets([_conference_line(c, talks) for c, talks in note.conferences]),
        "",
        "## Open",
        "",
        *_bullets(note.open_items),
        "",
        "## Sources",
        "",
        f"- Vault notes under Outputs/Publications, Outputs/Presentations, Honors, Awards, and Conferences, as of {assembled.isoformat()}.",
        "",
    ]
    return "\n".join(out)
