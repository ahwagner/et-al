"""The only module that touches the file system: notes, folders, and CSV files."""

from __future__ import annotations

import csv
import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.compat import ordereddict

YAML = YAML(typ="rt")
YAML.preserve_quotes = True
YAML.width = 4096
YAML.indent(mapping=2, sequence=4, offset=2)


@dataclass
class Note:
    path: Path
    name: str
    frontmatter: CommentedMap | None
    body: str
    parse_error: str | None


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Split a note into (yaml text, body); yaml is None when there is no frontmatter block."""
    if not text.startswith("---\n"):
        return None, text
    pos = 4
    while pos <= len(text):
        end = text.find("\n", pos)
        line = text[pos:] if end == -1 else text[pos:end]
        if line == "---":
            body = "" if end == -1 else text[end + 1 :]
            return text[4:pos], body
        if end == -1:
            break
        pos = end + 1
    return None, text


def read_note(path: Path) -> Note:
    text = path.read_text(encoding="utf-8")
    name = path.name[:-3] if path.name.endswith(".md") else path.stem
    yaml_text, body = split_frontmatter(text)
    if yaml_text is None:
        return Note(path, name, None, body, None)
    try:
        data = YAML.load(yaml_text)
    except Exception as exc:  # ruamel raises several YAMLError subclasses
        return Note(path, name, None, body, str(exc))
    if data is None:
        data = CommentedMap()
    if not isinstance(data, CommentedMap):
        return Note(path, name, None, body, "frontmatter is not a mapping")
    return Note(path, name, data, body, None)


def read_folder(folder: Path) -> list[Note]:
    if not folder.is_dir():
        return []
    return [read_note(p) for p in sorted(folder.glob("*.md"), key=lambda p: p.name) if p.is_file()]


def write_frontmatter(note: Note, updates: dict[str, object]) -> None:
    if note.frontmatter is None:
        raise ValueError(f"{note.name} has no frontmatter to update")
    for key, value in updates.items():
        if key in note.frontmatter:
            # CommentedMap.__setitem__ would re-wrap a plain str in the old value's quote style;
            # bypass it so the new value is emitted in the style YAML picks for it.
            ordereddict.__setitem__(note.frontmatter, key, value)
        else:
            note.frontmatter[key] = value
    buffer = io.StringIO()
    YAML.dump(note.frontmatter, buffer)
    yaml_text = buffer.getvalue()
    if yaml_text.endswith("...\n"):
        yaml_text = yaml_text[: -len("...\n")]
    if not yaml_text.endswith("\n"):
        yaml_text += "\n"
    write_text(note.path, f"---\n{yaml_text}---\n{note.body}")


def write_text(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def exists(path: Path) -> bool:
    return path.exists()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def append_csv_rows(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Append rows, creating the file with a header if absent. Atomic via temp file + os.replace."""
    buffer = io.StringIO(newline="")
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        buffer.write(existing)
        if existing and not existing.endswith("\n"):
            buffer.write("\n")
    writer = csv.writer(buffer, lineterminator="\n")
    if not path.exists():
        writer.writerow(header)
    writer.writerows(rows)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(buffer.getvalue())
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
