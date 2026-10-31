"""Prepare a vault for etal: config file, folders, Bases view files, and the user's People note."""

from __future__ import annotations

from pathlib import Path

from etal.config import CONFIG_NAME, DEFAULT_CONFIG_TEXT, DEFAULT_FOLDERS, load_config
from etal.vault import exists, write_text

_BASE_TEMPLATE = """\
filters:
  and:
    - file.inFolder("{folder}")
views:
  - type: table
    name: {name}
    order:
{columns}
    sort:
      - property: date
        direction: DESC
"""


def _base(folder: str, name: str, columns: list[str]) -> str:
    return _BASE_TEMPLATE.format(
        folder=folder, name=name, columns="\n".join(f"      - {c}" for c in columns)
    )


_PUBLICATION_COLUMNS = ["title", "date", "journal", "citations", "peer_reviewed", "grants"]
_PRESENTATION_COLUMNS = ["date", "format", "attendance", "event", "presenters", "audience", "grants"]

PUBLICATIONS_BASE = _base(DEFAULT_FOLDERS["publications"], "Publications", _PUBLICATION_COLUMNS)
PRESENTATIONS_BASE = _base(DEFAULT_FOLDERS["presentations"], "Presentations", _PRESENTATION_COLUMNS)

ALEX_NOTE = """\
---
aliases:
  - Wagner AH
  - Wagner A
  - Wagner, AH
  - Wagner, A
  - Alex Wagner
  - Alex H. Wagner
orcid: 0000-0002-2502-8961
scholar_id: cwG4QRAAAAAJ
lab_member: true
---
# Alex Wagner
"""


def run(root: Path, dry_run: bool) -> list[Path]:
    """Create what is missing and return those paths. Never overwrites.

    An existing etal.yaml decides the folders (ConfigError if it is invalid);
    without one, the default config and folders are used.
    """
    wanted: list[tuple[Path, str | None]] = []
    config_path = root / CONFIG_NAME
    if exists(config_path):
        folders = load_config(root).folders
    else:
        folders = DEFAULT_FOLDERS
        wanted.append((config_path, DEFAULT_CONFIG_TEXT))
    # "history" is a CSV file path, not a folder
    wanted += [(root / folder, None) for key, folder in folders.items() if key != "history"]
    for key, name, columns in (
        ("publications", "Publications", _PUBLICATION_COLUMNS),
        ("presentations", "Presentations", _PRESENTATION_COLUMNS),
    ):
        folder = folders[key]
        base_path = root / (Path(folder).parent / f"{name}.base")
        wanted.append((base_path, _base(Path(folder).as_posix(), name, columns)))
    wanted.append((root / folders["people"] / "Alex Wagner.md", ALEX_NOTE))
    created: list[Path] = []
    for path, text in wanted:
        if exists(path):
            continue
        created.append(path)
        if dry_run:
            continue
        if text is None:
            path.mkdir(parents=True, exist_ok=True)  # vault has no directory helper
        else:
            path.parent.mkdir(parents=True, exist_ok=True)  # vault has no directory helper
            write_text(path, text)
    return created
