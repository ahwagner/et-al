import datetime as dt
from pathlib import Path
from etal.vault import read_note, read_folder, write_frontmatter, append_csv_rows, read_csv_rows

SAMPLE = '''---
type: publication
title: "DGIdb 5.0: rebuilding"
date: 2024-01-05
pmid: "37953380"
grants:
  - "[[CIViC U24]]"
---
# DGIdb 5.0

Body text stays.
'''

def test_read_note(tmp_path):
    p = tmp_path / "2024 DGIdb 5.0.md"; p.write_text(SAMPLE)
    n = read_note(p)
    assert n.name == "2024 DGIdb 5.0"
    assert n.frontmatter["type"] == "publication"
    assert n.frontmatter["date"] == dt.date(2024, 1, 5)
    assert n.frontmatter["pmid"] == "37953380"
    assert n.body == "# DGIdb 5.0\n\nBody text stays.\n"
    assert n.parse_error is None

def test_note_without_frontmatter(tmp_path):
    p = tmp_path / "Plain.md"; p.write_text("# Epic\n- Follow up\n")
    n = read_note(p)
    assert n.frontmatter is None and n.parse_error is None and n.body.startswith("# Epic")

def test_bad_yaml_reports_error(tmp_path):
    p = tmp_path / "Bad.md"; p.write_text("---\ntitle: [unclosed\n---\nbody\n")
    n = read_note(p)
    assert n.frontmatter is None and n.parse_error

EXPECTED_AFTER_SYNC = '''---
type: publication
title: "DGIdb 5.0: rebuilding"
date: 2024-01-05
pmid: "37953380"
grants:
  - "[[CIViC U24]]"
citations: 458
citations_as_of: 2026-10-30
---
# DGIdb 5.0

Body text stays.
'''

def test_round_trip_preserves_everything_else(tmp_path):
    p = tmp_path / "n.md"; p.write_text(SAMPLE)
    n = read_note(p)
    write_frontmatter(n, {"citations": 458, "citations_as_of": dt.date(2026, 10, 30)})
    assert p.read_text() == EXPECTED_AFTER_SYNC

def test_update_existing_key_keeps_position(tmp_path):
    p = tmp_path / "n.md"; p.write_text(SAMPLE)
    n = read_note(p)
    write_frontmatter(n, {"title": "New title"})
    lines = p.read_text().splitlines()
    assert lines[1] == "type: publication" and lines[2] == "title: New title"

def test_read_folder_sorted_and_missing(tmp_path):
    (tmp_path / "b.md").write_text("x"); (tmp_path / "a.md").write_text("y"); (tmp_path / "c.txt").write_text("z")
    assert [n.name for n in read_folder(tmp_path)] == ["a", "b"]
    assert read_folder(tmp_path / "nope") == []

def test_csv_append_is_cumulative(tmp_path):
    p = tmp_path / "h.csv"
    append_csv_rows(p, ["as_of", "note", "scholar_id", "citations"], [["2026-10-30", "2024 DGIdb 5.0", "x:1", "458"]])
    append_csv_rows(p, ["as_of", "note", "scholar_id", "citations"], [["2026-10-31", "2024 DGIdb 5.0", "x:1", "460"]])
    rows = read_csv_rows(p)
    assert [r["citations"] for r in rows] == ["458", "460"]
    assert p.read_text().splitlines()[0] == "as_of,note,scholar_id,citations"


def test_write_frontmatter_keeps_file_mode(tmp_path):
    import os, stat
    p = tmp_path / "n.md"; p.write_text(SAMPLE)
    os.chmod(p, 0o644)
    write_frontmatter(read_note(p), {"citations": 458})
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o644
    os.chmod(p, 0o640)
    write_frontmatter(read_note(p), {"citations": 459})
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o640


def test_new_file_gets_the_umask_mode(tmp_path):
    import os, stat
    from etal.vault import write_text
    old = os.umask(0o022)
    try:
        write_text(tmp_path / "new.md", "x\n")
    finally:
        os.umask(old)
    assert stat.S_IMODE(os.stat(tmp_path / "new.md").st_mode) == 0o644


def test_failed_write_leaves_the_note_whole(tmp_path):
    import pytest
    from etal.vault import write_text
    p = tmp_path / "n.md"; p.write_text(SAMPLE)
    with pytest.raises(UnicodeEncodeError):
        write_text(p, "---\ntitle: \ud800\n---\n")      # a lone surrogate cannot be encoded
    assert p.read_text() == SAMPLE
    assert [x.name for x in tmp_path.iterdir()] == ["n.md"]


def test_write_through_a_symlink_keeps_the_link(tmp_path):
    from etal.vault import write_text
    real = tmp_path / "real.md"; real.write_text("old\n")
    link = tmp_path / "link.md"; link.symlink_to(real)
    write_text(link, "new\n")
    assert link.is_symlink() and real.read_text() == "new\n"
