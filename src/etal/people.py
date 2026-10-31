"""Name matching and authorship flags. Every comparison of printed names lives here."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from etal.schema import Person, Publication

__all__ = ["normalize_name", "AliasIndex", "AuthorFlags", "author_flags", "is_author"]


def normalize_name(s: str) -> str:
    """NFC-compose, strip, casefold, collapse whitespace to one space, drop trailing periods, strip again."""
    composed = unicodedata.normalize("NFC", s)
    return re.sub(r"\s+", " ", composed.strip().casefold()).rstrip(".").strip()


class AliasIndex:
    """Normalized alias (and the person's own note name) to the people who carry it."""

    def __init__(self, by_key: dict[str, list[Person]]) -> None:
        self._by_key = by_key

    @classmethod
    def build(cls, people: list[Person]) -> AliasIndex:
        by_key: dict[str, list[Person]] = {}
        for person in people:
            for printed in [person.name, *person.aliases]:
                key = normalize_name(printed)
                if not key:
                    continue
                holders = by_key.setdefault(key, [])
                if not any(p is person for p in holders):
                    holders.append(person)
        return cls(by_key)

    def candidates(self, printed: str) -> list[Person]:
        return list(self._by_key.get(normalize_name(printed), []))

    def resolve(self, printed: str) -> Person | None:
        found = self.candidates(printed)
        return found[0] if len(found) == 1 else None

    def is_person(self, printed: str, person: Person) -> bool:
        return any(p is person for p in self._by_key.get(normalize_name(printed), []))


@dataclass(frozen=True)
class AuthorFlags:
    first: bool
    senior_or_corresponding: bool
    peer_reviewed: bool

    @property
    def first_or_corresponding_peer_reviewed(self) -> bool:
        return (self.first or self.senior_or_corresponding) and self.peer_reviewed


def author_flags(pub: Publication, person: Person, index: AliasIndex) -> AuthorFlags:
    def named(names: list[str]) -> bool:
        return any(index.is_person(n, person) for n in names)

    authors = pub.authors
    first = named(authors[:1]) or named(pub.co_first)
    senior = (
        named(pub.corresponding)
        or (not pub.senior and named(authors[-1:]))
        or named(pub.senior)
    )
    return AuthorFlags(first, senior, pub.peer_reviewed)


def is_author(pub: Publication, person: Person, index: AliasIndex) -> bool:
    return any(index.is_person(n, person) for n in pub.authors)
