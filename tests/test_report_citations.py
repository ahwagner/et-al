import dataclasses
from pathlib import Path
from click.testing import CliRunner
from etal.cli import main
from etal.reports import citations

GOLDEN = Path(__file__).parent / "golden"

def fixed(vault_path):
    (vault_path / "Conferences" / "Unframed Meeting.md").unlink()
    (vault_path / "Outputs" / "Publications" / "2026 Unresolved import.md").unlink()
    return vault_path

def test_grouping_and_totals(data):
    r = citations.build(data)
    assert [s.name for s in r.stages] == ["Predoctoral", "Postdoctoral", "Nationwide Children's Hospital"]
    pre = r.stages[0]
    assert [row.title[:9] for row in pre.rows] == ["Exon-leve", "Whole-gen"]       # SAT1 pulled in by stage override
    assert (pre.totals.count, pre.totals.citations, pre.totals.first, pre.totals.senior) == (2, 142, 1, 0)
    assert r.stages[1].rows == []
    nch = r.stages[2]
    assert [row.title[:7] for row in nch.rows] == ["DGIdb 5", "Mapping", "Searchi", "The GA4"]   # by date within the stage
    assert (nch.totals.count, nch.totals.citations, nch.totals.first, nch.totals.senior) == (4, 471, 0, 3)
    assert (r.grand.count, r.grand.citations) == (6, 613)
    assert (r.fcpr_count, r.fcpr_citations) == (4, 601)
    assert r.oldest_as_of is not None

def test_merge_superseded(data):
    without = citations.build(data, statuses={"published", "accepted", "preprint"})
    assert without.grand.count == 7
    data.config = dataclasses.replace(data.config, merge_superseded=True)   # Config is frozen
    r = citations.build(data, statuses={"published", "accepted", "preprint"})
    assert r.grand.count == 6
    catvrs = next(row for s in r.stages for row in s.rows if row.title.startswith("The GA4GH Categorical"))
    assert catvrs.citations == 5

def test_filters(data):
    r = citations.build(data, statuses={"preprint"})
    assert r.grand.count == 1
    r = citations.build(data, person_name="Kori Kuzma")
    assert r.grand.count == 2        # Kuzma K is on DGIdb 5.0 and MAVE mapping

def test_golden_outputs(vault_path):
    fixed(vault_path)
    for fmt, name in [("md", "citations.md"), ("csv", "citations.csv")]:
        r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "citations", "--output", fmt])
        assert r.exit_code == 0, r.output
        assert r.output == (GOLDEN / name).read_text()

def test_markdown_has_sheet_columns(vault_path):
    fixed(vault_path)
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "report", "citations", "--as-of"])
    assert "| Title | Date | Journal | Citations | First / co-first | Senior / Corresponding | Peer Reviewed | First or Corresponding and Peer Reviewed |" in r.output
    assert "Grand Total" in r.output and "First or Corresponding Peer Reviewed Total" in r.output
    assert "Counts as of 2026-10-30" in r.output
