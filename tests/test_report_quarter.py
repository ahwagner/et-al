import datetime as dt
from pathlib import Path
from click.testing import CliRunner
from etal.cli import main
from etal.reports.quarter import Quarter, build, render, in_window
from etal.dates import PartialDate

GOLDEN = Path(__file__).parent / "golden" / "quarter-2026-Q3.md"

def fixed(vault_path):
    (vault_path / "Conferences" / "Unframed Meeting.md").unlink()
    (vault_path / "Outputs" / "Publications" / "2026 Unresolved import.md").unlink()
    return vault_path

def test_quarter_parse():
    q = Quarter.parse("2026-Q3")
    assert (q.start, q.end, q.label, q.previous.label) == (dt.date(2026, 7, 1), dt.date(2026, 9, 30), "2026-Q3", "2026-Q2")
    assert q.month_names == "July through September 2026"

def test_in_window_month_only():
    assert in_window(PartialDate.parse("2026-07"), dt.date(2026, 7, 1), dt.date(2026, 9, 30))
    assert not in_window(PartialDate.parse("2026-06"), dt.date(2026, 7, 1), dt.date(2026, 9, 30))

def test_sections(data):
    n = build(data, Quarter.parse("2026-Q3"))
    assert [p.note.name for p in n.self_publications] == ["2026 Druggable genome LLM"]
    assert [p.note.name for p in n.accepted] == ["2026 Cat-VRS"]
    assert [p.note.name for p in n.self_presentations] == ["2026-08-03 ClinVar automation CGC"]
    assert [p.note.name for p in n.lab_presentations] == ["2026-07 AnyVar research in review", "2026-07-12 Cat-VRS ISMB", "2026-08-05 FUSOR poster"]
    assert [h.name for h in n.honors] == ["GA4GH travel award"]
    assert [a.name for a in n.funding] == []            # R03 started in Q2
    assert [c.name for c, _ in n.conferences] == ["ISMB 2026", "CGC Annual Meeting 2026"]
    assert any("Day not recorded" in s or "day not recorded" in s for s in n.open_items)
    assert n.lookback_items == []                       # June talk is already in the 2026-Q2 note

def test_lookback_reports_unlisted_items(vault_path, data):
    (vault_path / "Outputs" / "2026-Q2 outputs.md").unlink()
    from etal import schema; from etal.config import load_config
    n = build(schema.load(load_config(vault_path)), Quarter.parse("2026-Q3"))
    assert [p.note.name for p in n.lookback_items] == ["2026-06-20 Prior quarter talk"]

def test_golden(vault_path):
    fixed(vault_path)
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "quarter", "2026-Q3", "--stdout"], env={"ETAL_TODAY": "2026-10-07"})
    assert r.exit_code == 0, r.output
    assert r.output == GOLDEN.read_text()

def test_writes_note_once(vault_path):
    fixed(vault_path)
    target = vault_path / "Outputs" / "2026-Q3 outputs.md"
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "quarter", "2026-Q3"], env={"ETAL_TODAY": "2026-10-07"})
    assert r.exit_code == 0 and target.exists()
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "quarter", "2026-Q3"], env={"ETAL_TODAY": "2026-10-07"})
    assert "already exists" in r.output and "## Publications" in r.output

def test_previous_wraps_year_and_bad_label():
    q = Quarter.parse("2026-Q1")
    assert (q.previous.label, q.month_names) == ("2025-Q4", "January through March 2026")
    for bad in ("2026-Q5", "2026Q3", "Q3"):
        try:
            Quarter.parse(bad)
        except ValueError:
            continue
        raise AssertionError(bad)

def test_cli_rejects_bad_quarter(vault_path):
    fixed(vault_path)
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "quarter", "2026-Q9"])
    assert r.exit_code != 0 and "2026-Q9" in r.output

def test_stdout_and_dry_run_write_nothing(vault_path):
    fixed(vault_path)
    target = vault_path / "Outputs" / "2026-Q3 outputs.md"
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "quarter", "2026-Q3", "--stdout"])
    assert r.exit_code == 0 and not target.exists()
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "quarter", "2026-Q3", "--dry-run"])
    assert r.exit_code == 0 and not target.exists()
    assert r.output.startswith("Would write Outputs/2026-Q3 outputs.md\n---\ntype: outputs")

def test_existing_note_is_not_overwritten(vault_path):
    fixed(vault_path)
    target = vault_path / "Outputs" / "2026-Q3 outputs.md"
    target.write_text("mine\n")
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "quarter", "2026-Q3"])
    assert r.output.startswith("Outputs/2026-Q3 outputs.md already exists; printing instead.\n---\n")
    assert target.read_text() == "mine\n"

def test_lookback_two_months_heading(data):
    q = Quarter.parse("2026-Q3")
    text = render(build(data, q, lookback=2), q, dt.date(2026, 10, 7))
    assert "## Checked back to May and June" in text
    assert "checked back to May and June." in text
    assert "Checked back" not in render(build(data, q, lookback=0), q, dt.date(2026, 10, 7))
