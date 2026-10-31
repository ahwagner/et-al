"""Configuration: etal.yaml and vault discovery."""
from __future__ import annotations

import datetime as dt
import os
import re
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from etal.dates import PartialDate

CONFIG_NAME = "etal.yaml"

DEFAULT_FOLDERS = {
    "publications": "Outputs/Publications",
    "presentations": "Outputs/Presentations",
    "journals": "Journals",
    "conferences": "Conferences",
    "honors": "Honors",
    "awards": "Awards",
    "people": "People",
    "history": "Outputs/citation-history.csv",
}

DEFAULT_CONFIG_TEXT = """\
self: "[[Alex Wagner]]"
scholar_profile: cwG4QRAAAAAJ
career_stages:           # reports group publications by the stage containing date, unless the note sets stage
  - name: Predoctoral
    until: 2014-12-31    # PhD, University of Iowa, completed 12/2014
  - name: Postdoctoral
    until: 2020-08-02    # postdoctoral fellow 01/2015 to 07/2019, then Instructor of Medicine, Washington University, to 08/2020
  - name: Nationwide Children's Hospital   # Principal Investigator from 2020-08-03; Associate Professor from 2026-06-04
merge_superseded: false
folders:                 # defaults shown; override only if the vault moves them
  publications: Outputs/Publications
  presentations: Outputs/Presentations
  journals: Journals
  conferences: Conferences
  honors: Honors
  awards: Awards
  people: People
  history: Outputs/citation-history.csv
"""

_WIKILINK = re.compile(r"^\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]$")


class ConfigError(Exception):
    """Raised when etal.yaml or the vault location is invalid."""


def parse_wikilink(value: str) -> str | None:
    """Return the note name a wikilink points to, or None if value is not a wikilink."""
    match = _WIKILINK.match(value.strip())
    if match is None:
        return None
    name = match.group(1).strip().rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    return name


@dataclass(frozen=True)
class Stage:
    name: str
    until: dt.date | None


@dataclass(frozen=True)
class Config:
    root: Path
    self_name: str
    scholar_profile: str
    career_stages: list[Stage]
    merge_superseded: bool
    folders: dict[str, str]

    def folder(self, key: str) -> Path:
        return self.root / self.folders[key]

    @property
    def history_path(self) -> Path:
        return self.folder("history")

    @property
    def stage_names(self) -> list[str]:
        return [stage.name for stage in self.career_stages]

    def stage_for(self, d: PartialDate) -> str:
        first = d.first_day()
        for stage in self.career_stages:
            if stage.until is None or stage.until >= first:
                return stage.name
        return self.career_stages[-1].name


def _until(value: object, where: str) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            pass
    raise ConfigError(f"{CONFIG_NAME}: {where}: expected an ISO date, got {value!r}")


def load_config(root: Path) -> Config:
    path = root / CONFIG_NAME
    if not path.is_file():
        raise ConfigError(f"{path}: not found; run `etal init`")
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a mapping at the top level")

    for field in ("self", "scholar_profile", "career_stages"):
        if not data.get(field):
            raise ConfigError(f"{path}: {field}: required")

    self_name = parse_wikilink(str(data["self"]))
    if self_name is None:
        raise ConfigError(f"{path}: self: expected a wikilink such as [[Alex Wagner]]")

    raw_stages = data["career_stages"]
    if not isinstance(raw_stages, list):
        raise ConfigError(f"{path}: career_stages: expected a list")
    stages: list[Stage] = []
    for index, raw in enumerate(raw_stages):
        where = f"career_stages[{index}]"
        if not isinstance(raw, dict) or not raw.get("name"):
            raise ConfigError(f"{path}: {where}.name: required")
        until = _until(raw.get("until"), f"{where}.until")
        if until is None and index < len(raw_stages) - 1:
            raise ConfigError(f"{path}: {where}.until: required on every stage but the last")
        stages.append(Stage(str(raw["name"]), until))

    overrides = data.get("folders") or {}
    if not isinstance(overrides, dict):
        raise ConfigError(f"{path}: folders: expected a mapping")
    folders = {**DEFAULT_FOLDERS, **{str(k): str(v) for k, v in overrides.items()}}

    return Config(
        root=root,
        self_name=self_name,
        scholar_profile=str(data["scholar_profile"]),
        career_stages=stages,
        merge_superseded=bool(data.get("merge_superseded", False)),
        folders=folders,
    )


def find_vault(cli_value: str | None) -> Path:
    """CLI value, else ETAL_VAULT, else the current directory if it holds etal.yaml."""
    if cli_value:
        return Path(cli_value).expanduser()
    env = os.environ.get("ETAL_VAULT")
    if env:
        return Path(env).expanduser()
    cwd = Path.cwd()
    if (cwd / CONFIG_NAME).is_file():
        return cwd
    raise ConfigError(
        f"no vault: pass --vault, set ETAL_VAULT, or run from a folder holding {CONFIG_NAME}"
    )
