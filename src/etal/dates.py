"""Partial dates: a year, a year and month, or a full day."""
from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass
from typing import Literal

_PATTERN = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
_RANK = {"year": 0, "month": 1, "day": 2}


@dataclass(frozen=True)
class PartialDate:
    year: int
    month: int | None = None
    day: int | None = None

    def __post_init__(self) -> None:
        if self.month is None and self.day is not None:
            raise ValueError("a day requires a month")
        # Range checks: date() raises ValueError on a bad year, month, or day.
        dt.date(self.year, self.month or 1, self.day or 1)

    @classmethod
    def parse(cls, value: str | int | dt.date | dt.datetime) -> PartialDate:
        # datetime is a subclass of date, so it must be handled first.
        if isinstance(value, dt.datetime):
            return cls(value.year, value.month, value.day)
        if isinstance(value, dt.date):
            return cls(value.year, value.month, value.day)
        if isinstance(value, bool):
            raise ValueError(f"cannot parse a date from {value!r}")
        if isinstance(value, int):
            return cls(value)
        if isinstance(value, str):
            match = _PATTERN.match(value.strip())
            if match is None:
                raise ValueError(f"cannot parse a date from {value!r}")
            year, month, day = match.groups()
            return cls(int(year), int(month) if month else None, int(day) if day else None)
        raise ValueError(f"cannot parse a date from {value!r}")

    @property
    def precision(self) -> Literal["year", "month", "day"]:
        if self.day is not None:
            return "day"
        if self.month is not None:
            return "month"
        return "year"

    @property
    def day_recorded(self) -> bool:
        return self.day is not None

    def first_day(self) -> dt.date:
        return dt.date(self.year, self.month or 1, self.day or 1)

    def last_day(self) -> dt.date:
        if self.day is not None:
            return dt.date(self.year, self.month, self.day)
        month = self.month or 12
        return dt.date(self.year, month, calendar.monthrange(self.year, month)[1])

    def _key(self) -> tuple[dt.date, int]:
        return (self.first_day(), _RANK[self.precision])

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PartialDate):
            return NotImplemented
        return self._key() < other._key()

    def __str__(self) -> str:
        if self.day is not None:
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        if self.month is not None:
            return f"{self.year:04d}-{self.month:02d}"
        return f"{self.year:04d}"
