from click.testing import CliRunner
from etal import schema
from etal.cli import main
from etal.config import load_config

def problems(vault_path):
    return {(p.path.name, p.field): p.message for p in schema.validate(schema.load(load_config(vault_path)))}

def test_fixture_has_only_the_planted_problems(vault_path):
    assert set(problems(vault_path)) == {("Unframed Meeting.md", "type"), ("2026 Unresolved import.md", "authors")}

def test_required_and_enumerated(vault_path):
    p = vault_path / "Outputs" / "Presentations" / "2026-08-03 ClinVar automation CGC.md"
    p.write_text(p.read_text().replace("attendance: in person", "attendance: hybrid").replace("format: invited talk", ""))
    probs = problems(vault_path)
    assert "in person | virtual" in probs[("2026-08-03 ClinVar automation CGC.md", "attendance")]
    assert ("2026-08-03 ClinVar automation CGC.md", "format") in probs

def test_wrong_type_for_folder(vault_path):
    p = vault_path / "Conferences" / "ISMB 2026.md"
    p.write_text(p.read_text().replace("type: conference", "type: meeting-series"))
    assert ("ISMB 2026.md", "type") in problems(vault_path)

def test_unresolved_link_and_folder(vault_path):
    p = vault_path / "Outputs" / "Publications" / "2024 DGIdb 5.0.md"
    p.write_text(p.read_text().replace('"[[R35]]"', '"[[R99]]"'))
    assert "Awards" in problems(vault_path)[("2024 DGIdb 5.0.md", "grants")]

def test_presentation_date_outside_event(vault_path):
    p = vault_path / "Outputs" / "Presentations" / "2026-08-03 ClinVar automation CGC.md"
    p.write_text(p.read_text().replace("date: 2026-08-03", "date: 2026-09-03"))
    assert ("2026-08-03 ClinVar automation CGC.md", "date") in problems(vault_path)

def test_duplicate_doi_and_issn(vault_path):
    p = vault_path / "Outputs" / "Publications" / "2025 MAVE mapping.md"
    p.write_text(p.read_text().replace("10.1186/s13059-025-03647-x", "10.1093/nar/gkad1040"))
    j = vault_path / "Journals" / "Genome Biology.md"
    j.write_text(j.read_text().replace("issn: 1474-760X", "issn: 0305-1048", 1))
    probs = problems(vault_path)
    assert ("2025 MAVE mapping.md", "doi") in probs and ("Genome Biology.md", "issn") in probs

def test_ambiguous_alias(vault_path):
    (vault_path / "People" / "Kori Kuzma Two.md").write_text("---\naliases:\n  - Kuzma K\nlab_member: true\n---\n# Kori Kuzma Two\n")
    assert ("2025 MAVE mapping.md", "authors") in problems(vault_path)

def test_unknown_stage(vault_path):
    p = vault_path / "Outputs" / "Publications" / "2016 SAT1.md"
    p.write_text(p.read_text().replace("stage: Predoctoral", "stage: Graduate"))
    assert "Predoctoral | Postdoctoral" in problems(vault_path)[("2016 SAT1.md", "stage")]

def test_cli_exit_codes(vault_path):
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "validate"])
    assert r.exit_code == 1 and "Unframed Meeting.md: type:" in r.output and r.output.rstrip().endswith("2 problems")
    (vault_path / "Conferences" / "Unframed Meeting.md").write_text("---\ntype: conference\nname: Unframed Meeting\nstart: 2026-01-01\nlocation: Virtual\naudience: local\n---\n# Unframed Meeting\n")
    p = vault_path / "Outputs" / "Publications" / "2026 Unresolved import.md"
    p.write_text(p.read_text().replace("authors: []", "authors:\n  - Wagner AH"))
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "validate"])
    assert r.exit_code == 0 and r.output.startswith("OK:")

def test_blank_title_only_for_hackathon_or_workshop(vault_path):
    p = vault_path / "Outputs" / "Presentations" / "2026-08-03 ClinVar automation CGC.md"
    text = p.read_text().replace("title: Automating somatic cancer submissions to ClinVar with GA4GH genomic knowledge standards", "title:")
    p.write_text(text)
    assert ("2026-08-03 ClinVar automation CGC.md", "title") in problems(vault_path)
    p.write_text(text.replace("format: invited talk", "format: hackathon"))
    assert ("2026-08-03 ClinVar automation CGC.md", "title") not in problems(vault_path)

def test_single_problem_is_singular(vault_path):
    (vault_path / "Conferences" / "Unframed Meeting.md").unlink()
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "validate"])
    assert r.exit_code == 1 and r.output.rstrip().endswith("\n1 problem")
