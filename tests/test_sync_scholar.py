# tests/test_sync_scholar.py
import datetime as dt
from pathlib import Path
from click.testing import CliRunner
from etal.cli import main
from etal.sync.scholar import normalize_title, works_from_json, match, plan, apply, last_sync_date
from etal.vault import read_note, read_csv_rows

FIX = Path(__file__).parent / "fixtures" / "scholar" / "profile.json"

def test_normalize_title():
    assert normalize_title("DGIdb 5.0: rebuilding the drug–gene interaction database") == normalize_title("dgidb 5 0 rebuilding the drug gene interaction database")
    assert normalize_title("Ĉat-VRS") == "cat vrs"

def test_match_by_id_then_title(data):
    r = match(works_from_json(FIX), data.publications)
    names = {p.note.name for p, _ in r.matched}
    assert names == {"2024 DGIdb 5.0", "2025 MAVE mapping", "2013 Exon-level expression", "2026 Cat-VRS preprint", "2026 Druggable genome LLM", "2016 SAT1"}
    assert {w.title for w in r.unmatched_works} == {"A paper not in the vault", "Another stray"}
    assert {p.note.name for p in r.unmatched_pubs} == {"2026 Cat-VRS", "2026 Unresolved import"}

def test_plan_lists_only_changes(data):
    r = match(works_from_json(FIX), data.publications)
    changes = {c.pub.note.name: (c.old, c.new, c.scholar_id_added) for c in plan(r, dt.date(2026, 10, 31))}
    assert changes["2024 DGIdb 5.0"] == (458, 470, True)
    assert changes["2026 Cat-VRS preprint"] == (3, 4, False)
    assert changes["2026 Druggable genome LLM"] == (1, 1, True)   # count unchanged, but the id is new
    assert len(changes) == 6

def test_apply_writes_frontmatter_history_and_sources(vault_path, data):
    r = match(works_from_json(FIX), data.publications)
    apply(data, r, dt.date(2026, 10, 31), dry_run=False)
    n = read_note(vault_path / "Outputs" / "Publications" / "2024 DGIdb 5.0.md")
    assert n.frontmatter["citations"] == 470 and n.frontmatter["scholar_id"] == "cwG4QRAAAAAJ:dgidb5"
    assert str(n.frontmatter["citations_as_of"]) == "2026-10-31"
    assert list(n.frontmatter["sources"])[-1] == "Google Scholar, 2026-10-31"
    assert n.body.startswith("# DGIdb 5.0")
    rows = read_csv_rows(data.config.history_path)
    assert len(rows) == 6 and {r["note"] for r in rows} >= {"2024 DGIdb 5.0", "2016 SAT1"}
    assert last_sync_date(data.config.history_path) == dt.date(2026, 10, 31)

def test_sources_not_duplicated_on_second_run(vault_path, data):
    r = match(works_from_json(FIX), data.publications)
    apply(data, r, dt.date(2026, 10, 31), dry_run=False)
    from etal import schema; from etal.config import load_config
    data2 = schema.load(load_config(vault_path))
    apply(data2, match(works_from_json(FIX), data2.publications), dt.date(2026, 11, 1), dry_run=False)
    n = read_note(vault_path / "Outputs" / "Publications" / "2024 DGIdb 5.0.md")
    assert [s for s in n.frontmatter["sources"] if s.startswith("Google Scholar")] == ["Google Scholar, 2026-10-31"]

def test_dry_run_touches_nothing(vault_path, data):
    before = (vault_path / "Outputs" / "Publications" / "2024 DGIdb 5.0.md").read_text()
    apply(data, match(works_from_json(FIX), data.publications), dt.date(2026, 10, 31), dry_run=True)
    assert (vault_path / "Outputs" / "Publications" / "2024 DGIdb 5.0.md").read_text() == before
    assert not data.config.history_path.exists()

def fixed(vault_path):
    (vault_path / "Conferences" / "Unframed Meeting.md").unlink()
    (vault_path / "Outputs" / "Publications" / "2026 Unresolved import.md").unlink()

def test_cli_guard_and_output(vault_path):
    fixed(vault_path)
    env = {"ETAL_SCHOLAR_FIXTURE": str(FIX), "ETAL_TODAY": "2026-10-31"}
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "sync", "scholar"], env=env)
    assert r.exit_code == 0, r.output
    assert "2024 DGIdb 5.0" in r.output and "458" in r.output and "470" in r.output
    assert "A paper not in the vault" in r.output and "2026 Cat-VRS" in r.output
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "sync", "scholar"], env=env)
    assert r.exit_code == 2 and "already synced today" in r.output
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "sync", "scholar", "--force", "--only", "2016 SAT1"], env=env)
    assert r.exit_code == 0 and "2024 DGIdb" not in r.output.split("Scholar works with no note")[0]

def test_cli_network_failure_writes_nothing(vault_path, monkeypatch):
    fixed(vault_path)
    import etal.sync.scholar as s
    def boom(profile_id): raise s.FetchError("blocked")
    monkeypatch.setattr(s, "fetch", boom)
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "sync", "scholar"], env={"ETAL_TODAY": "2026-10-31"})
    assert r.exit_code == 2 and "blocked" in r.output
    assert not (vault_path / "Outputs" / "citation-history.csv").exists()

def test_empty_profile(vault_path, tmp_path):
    fixed(vault_path)
    empty = tmp_path / "empty.json"; empty.write_text("[]")
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "sync", "scholar"], env={"ETAL_SCHOLAR_FIXTURE": str(empty), "ETAL_TODAY": "2026-10-31"})
    assert r.exit_code == 0 and "0 updated" in r.output


def test_ambiguous_title_is_left_unmatched(data):
    from etal.sync.scholar import ScholarWork
    cat = [p for p in data.publications if p.note.name in ("2026 Cat-VRS", "2026 Cat-VRS preprint")]
    r = match([ScholarWork("x:2", cat[0].title, 2026, 9)], cat)
    assert r.matched == [] and len(r.unmatched_works) == 1


def test_cli_dry_run_writes_nothing(vault_path):
    fixed(vault_path)
    target = vault_path / "Outputs" / "Publications" / "2024 DGIdb 5.0.md"
    before = target.read_text()
    env = {"ETAL_SCHOLAR_FIXTURE": str(FIX), "ETAL_TODAY": "2026-10-31"}
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "sync", "scholar", "--dry-run"], env=env)
    assert r.exit_code == 0 and "2024 DGIdb 5.0" in r.output and "470" in r.output
    assert target.read_text() == before
    assert not (vault_path / "Outputs" / "citation-history.csv").exists()
