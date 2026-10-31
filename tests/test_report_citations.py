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


def test_merge_superseded_under_default_filters(data):
    data.config = dataclasses.replace(data.config, merge_superseded=True)
    r = citations.build(data)
    assert r.grand.count == 6
    catvrs = next(row for s in r.stages for row in s.rows if row.title.startswith("The GA4GH Categorical"))
    assert catvrs.citations == 5          # 2 on the accepted paper + 3 on the preprint it supersedes


def _write_earlier_preprint(vault_path):
    pubs = vault_path / "Outputs" / "Publications"
    text = (pubs / "2026 Cat-VRS preprint.md").read_text()
    text = text.replace("scholar_id: cwG4QRAAAAAJ:catvrs1", "scholar_id:").replace("citations: 3", "citations: 7")
    text = text.replace("date: 2026-04-30", "date: 2026-01-15").replace("# Cat-VRS preprint", "# Cat-VRS preprint v1")
    (pubs / "2026 Cat-VRS preprint v1.md").write_text(text)
    preprint = pubs / "2026 Cat-VRS preprint.md"
    preprint.write_text(preprint.read_text().replace("supersedes:\n", 'supersedes: "[[2026 Cat-VRS preprint v1]]"\n', 1))


def test_merge_superseded_follows_a_chain(vault_path):
    _write_earlier_preprint(vault_path)
    from etal import schema
    from etal.config import load_config
    data = schema.load(load_config(vault_path))
    data.config = dataclasses.replace(data.config, merge_superseded=True)
    for statuses in (None, {"published", "accepted", "preprint"}):
        r = citations.build(data, statuses=statuses)
        assert r.grand.count == 6
        catvrs = next(row for s in r.stages for row in s.rows if row.title.startswith("The GA4GH Categorical"))
        assert catvrs.citations == 12     # 2 + 3 + 7: both predecessors fold in


def test_merge_superseded_survives_self_link_and_cycle(data):
    data.config = dataclasses.replace(data.config, merge_superseded=True)
    pubs = data.by_name["publications"]
    sat1, mave = pubs["2016 SAT1"], pubs["2025 MAVE mapping"]
    sat1.supersedes = sat1
    r = citations.build(data)
    assert r.grand.count == 6
    sat1.supersedes, mave.supersedes = mave, sat1
    r = citations.build(data)
    titles = [row.title for s in r.stages for row in s.rows]
    assert sat1.title in titles and mave.title in titles
