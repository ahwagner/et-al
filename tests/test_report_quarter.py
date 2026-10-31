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
    assert r.output == "Wrote Outputs/2026-Q3 outputs.md\n"
    assert target.read_text() == GOLDEN.read_text()
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

def _render(data, label, lookback=1):
    q = Quarter.parse(label)
    return render(build(data, q, lookback), q, dt.date(2026, 10, 7))

def test_funding_line(data):
    text = _render(data, "2026-Q2")
    assert "## Funding\n\n- 2026-05-01 | R03. R03HG014803. NHGRI. Contact PI.\n" in text

def test_checked_back_section_renders_full_line(vault_path):
    (vault_path / "Outputs" / "2026-Q2 outputs.md").unlink()
    from etal import schema; from etal.config import load_config
    data = schema.load(load_config(vault_path))
    talk = next(p for p in data.presentations if p.note.name == "2026-06-20 Prior quarter talk")
    from etal.render import presentation_line
    text = _render(data, "2026-Q3")
    assert f"## Checked back to June\n\n- 2026-06-20 | {presentation_line(talk)}\n\n## Presentations" in text

def test_lab_publication_without_alex(vault_path):
    note = vault_path / "Outputs" / "Publications" / "2026 Lab only paper.md"
    note.write_text("""---
type: publication
title: A lab only paper
format: article
status: published
date: 2026-08-10
journal: "[[Genome Biology]]"
volume:
issue:
pages:
authors:
  - Kuzma K
  - Cannon M
co_first: []
corresponding: []
senior: []
peer_reviewed:
doi:
pmid:
pmcid:
url:
scholar_id:
citations:
citations_as_of:
grants: []
supersedes:
stage:
sources: []
notes:
---
# Lab only paper
""")
    from etal import schema; from etal.config import load_config
    from etal.render import nlm_citation
    data = schema.load(load_config(vault_path))
    n = build(data, Quarter.parse("2026-Q3"))
    assert [p.note.name for p in n.lab_publications] == ["2026 Lab only paper"]
    assert [p.note.name for p in n.self_publications] == ["2026 Druggable genome LLM"]
    text = _render(data, "2026-Q3")
    assert f"Lab, without Alex as an author:\n\n- 2026-08-10 | {nlm_citation(n.lab_publications[0])}\n" in text

def test_conference_line_order(data):
    text = _render(data, "2026-Q3")
    assert "- CGC Annual Meeting 2026, Houston, TX, 2026-08-01 to 2026-08-05. Invited talk, poster.\n" in text

def test_missing_self_person_stops(data):
    import pytest
    data.people = [p for p in data.people if p.name != "Alex Wagner"]
    del data.people_by_name["Alex Wagner"]
    with pytest.raises(ValueError, match="Alex Wagner"):
        build(data, Quarter.parse("2026-Q3"))

def test_cli_turns_missing_self_into_error(vault_path, monkeypatch):
    from etal import schema
    real = schema.load
    def load_without_self(config):
        d = real(config)
        d.people = [p for p in d.people if p.name != "Alex Wagner"]
        del d.people_by_name["Alex Wagner"]
        return d
    monkeypatch.setattr(schema, "load", load_without_self)
    monkeypatch.setattr(schema, "validate", lambda d: [])
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "quarter", "2026-Q3", "--stdout"])
    assert r.exit_code == 1 and "Alex Wagner" in r.output and "no People note" in r.output


def _write_pub(vault_path, name, title, status, fmt, date, journal="Bioinformatics"):
    (vault_path / "Outputs" / "Publications" / f"{name}.md").write_text(f"""---
type: publication
title: {title}
format: {fmt}
status: {status}
date: {date}
journal: "[[{journal}]]"
authors:
  - Kuzma K
  - Wagner AH
citations:
supersedes:
sources: []
---
# {name}
""")


def test_own_preprint_in_window_is_listed(vault_path):
    _write_pub(vault_path, "2026 Q3 preprint", "A preprint in the quarter", "preprint", "preprint", "2026-08-01", "bioRxiv")
    from etal import schema; from etal.config import load_config
    from etal.render import nlm_citation
    data = schema.load(load_config(vault_path))
    n = build(data, Quarter.parse("2026-Q3"))
    assert [p.note.name for p in n.self_publications] == ["2026 Q3 preprint", "2026 Druggable genome LLM"]
    text = _render(data, "2026-Q3")
    pre = data.by_name["publications"]["2026 Q3 preprint"]
    assert f"## Publications\n\n- 2026-08-01 | {nlm_citation(pre)}\n- 2026-08-22 | " in text


def test_own_submitted_paper_goes_to_open_only(vault_path):
    _write_pub(vault_path, "2026 Q3 submitted", "A submitted paper", "submitted", "article", "2026-08-15")
    _write_pub(vault_path, "2026 Q3 draft", "A draft paper", "in preparation", "article", "2026-09-01")
    from etal import schema; from etal.config import load_config
    data = schema.load(load_config(vault_path))
    n = build(data, Quarter.parse("2026-Q3"))
    listed = [p.note.name for p in (*n.self_publications, *n.accepted, *n.lab_publications)]
    assert "2026 Q3 submitted" not in listed and "2026 Q3 draft" not in listed
    assert "2026 Q3 submitted: status submitted, not listed" in n.open_items
    assert "2026 Q3 draft: status in preparation, not listed" in n.open_items
    text = _render(data, "2026-Q3")
    assert "A submitted paper" not in text and "A draft paper" not in text
    assert "- 2026 Q3 submitted: status submitted, not listed\n" in text


def test_lab_list_takes_only_listed_statuses(vault_path):
    for status in ("published", "accepted", "preprint", "submitted"):
        (vault_path / "Outputs" / "Publications" / f"2026 Lab {status}.md").write_text(f"""---
type: publication
title: Lab {status} paper
format: article
status: {status}
date: 2026-08-10
journal: "[[Genome Biology]]"
authors:
  - Kuzma K
sources: []
---
# Lab {status}
""")
    from etal import schema; from etal.config import load_config
    n = build(schema.load(load_config(vault_path)), Quarter.parse("2026-Q3"))
    assert [p.note.name for p in n.lab_publications] == ["2026 Lab accepted", "2026 Lab preprint", "2026 Lab published"]
