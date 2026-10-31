from collections import defaultdict

from click.testing import CliRunner
from etal import schema
from etal.cli import main
from etal.config import load_config

PUBS = "Outputs/Publications"
PRES = "Outputs/Presentations"
CLINVAR = "2026-08-03 ClinVar automation CGC.md"


def problems(vault_path):
    """(note name, field) -> every message reported there, so a double report shows."""
    found = defaultdict(list)
    for p in schema.validate(schema.load(load_config(vault_path))):
        found[(p.path.name, p.field)].append(p.message)
    return found


def one(probs, name, field):
    """The single message reported for a field. Fails on none and on a double report."""
    messages = probs.get((name, field), [])
    assert len(messages) == 1, f"{name}: {field}: {messages}"
    return messages[0]


def edit(vault_path, folder, name, old, new):
    path = vault_path / folder / name
    text = path.read_text()
    assert old in text, f"{old!r} not in {name}"
    path.write_text(text.replace(old, new, 1))


def test_fixture_has_only_the_planted_problems(vault_path):
    probs = problems(vault_path)
    assert set(probs) == {("Unframed Meeting.md", "type"), ("2026 Unresolved import.md", "authors")}
    assert all(len(messages) == 1 for messages in probs.values())


def test_required_and_enumerated(vault_path):
    edit(vault_path, PRES, CLINVAR, "attendance: in person", "attendance: hybrid")
    edit(vault_path, PRES, CLINVAR, "format: invited talk", "")
    probs = problems(vault_path)
    assert "in person | virtual" in one(probs, CLINVAR, "attendance")
    assert one(probs, CLINVAR, "format") == "required"


def test_required_links_and_lists(vault_path):
    edit(vault_path, PUBS, "2024 DGIdb 5.0.md", 'journal: "[[Nucleic Acids Research]]"', "journal:")
    edit(vault_path, PRES, CLINVAR, 'event: "[[CGC Annual Meeting 2026]]"', "event:")
    edit(vault_path, PRES, CLINVAR, 'presenters:\n  - "[[Alex Wagner]]"', "presenters: []")
    probs = problems(vault_path)
    assert one(probs, "2024 DGIdb 5.0.md", "journal") == "required"
    assert one(probs, CLINVAR, "event") == "required"
    assert one(probs, CLINVAR, "presenters") == "required"


def test_required_and_enumerated_on_conference_and_honor(vault_path):
    edit(vault_path, "Conferences", "CGC Annual Meeting 2026.md", "location: Houston, TX", "location:")
    edit(vault_path, "Conferences", "CGC Annual Meeting 2026.md", "audience: national", "audience: galactic")
    edit(vault_path, "Conferences", "ISMB 2026.md", "start:", "starts:")
    honor = "2026-09 GA4GH travel award.md"
    edit(vault_path, "Honors", honor, 'recipient: "[[Daniel Puthawala]]"', "recipient:")
    edit(vault_path, "Honors", honor, "name: GA4GH travel award", "name:")
    edit(vault_path, "Honors", honor, "result: won", "result: runner-up")
    probs = problems(vault_path)
    assert one(probs, "CGC Annual Meeting 2026.md", "location") == "required"
    assert "international | national" in one(probs, "CGC Annual Meeting 2026.md", "audience")
    assert one(probs, "ISMB 2026.md", "start") == "required"
    assert one(probs, honor, "recipient") == "required"
    assert one(probs, honor, "name") == "required"
    assert "won | nominated | finalist" in one(probs, honor, "result")


def test_required_on_journal_and_publication(vault_path):
    edit(vault_path, "Journals", "Genome Biology.md", "peer_reviewed: true", "peer_reviewed:")
    edit(vault_path, PUBS, "2016 SAT1.md", "status: published", "status: finished")
    probs = problems(vault_path)
    assert one(probs, "Genome Biology.md", "peer_reviewed") == "required"
    assert "published | accepted" in one(probs, "2016 SAT1.md", "status")


def test_wrong_type_for_folder(vault_path):
    edit(vault_path, "Conferences", "ISMB 2026.md", "type: conference", "type: meeting-series")
    assert "meeting-series" in one(problems(vault_path), "ISMB 2026.md", "type")


def test_unresolved_link_and_folder(vault_path):
    edit(vault_path, PUBS, "2024 DGIdb 5.0.md", '"[[R35]]"', '"[[R99]]"')
    assert "Awards" in one(problems(vault_path), "2024 DGIdb 5.0.md", "grants")


def test_presentation_date_outside_event(vault_path):
    edit(vault_path, PRES, CLINVAR, "date: 2026-08-03", "date: 2026-09-03")
    assert "CGC Annual Meeting 2026" in one(problems(vault_path), CLINVAR, "date")


def test_presentation_date_boundaries(vault_path):
    # The CGC event runs 2026-08-01 to 2026-08-05.
    for date, outside in [
        ("2026-07-31", True), ("2026-08-01", False), ("2026-08-05", False), ("2026-08-06", True),
        # A month-precision date is in range when any day of the month falls inside the event.
        ("2026-08", False), ("2026-07", True), ("2026-09", True),
    ]:
        edit(vault_path, PRES, CLINVAR, "date: 2026-08-03", f"date: {date}")
        assert (((CLINVAR, "date") in problems(vault_path)) == outside), date
        edit(vault_path, PRES, CLINVAR, f"date: {date}", "date: 2026-08-03")


def test_month_precision_date_inside_month_precision_event(vault_path):
    conf = "CGC Annual Meeting 2026.md"
    edit(vault_path, "Conferences", conf, "start: 2026-08-01", "start: 2026-08")
    edit(vault_path, "Conferences", conf, "end: 2026-08-05", "end: 2026-08")
    edit(vault_path, PRES, CLINVAR, "date: 2026-08-03", "date: 2026-08")
    assert (CLINVAR, "date") not in problems(vault_path)
    edit(vault_path, PRES, CLINVAR, "date: 2026-08", "date: 2026-09")
    assert (CLINVAR, "date") in problems(vault_path)


def test_single_day_event_constrains_the_date(vault_path):
    # No end given: the event is its start day only.
    conf = "CGC Annual Meeting 2026.md"
    edit(vault_path, "Conferences", conf, "end: 2026-08-05", "end:")
    edit(vault_path, PRES, CLINVAR, "date: 2026-08-03", "date: 2026-08-02")
    assert (CLINVAR, "date") in problems(vault_path)


def test_duplicate_doi_reports_both_notes(vault_path):
    edit(vault_path, PUBS, "2025 MAVE mapping.md", "10.1186/s13059-025-03647-x", "10.1093/nar/gkad1040")
    probs = problems(vault_path)
    assert "2025 MAVE mapping" in one(probs, "2024 DGIdb 5.0.md", "doi")
    assert "2024 DGIdb 5.0" in one(probs, "2025 MAVE mapping.md", "doi")


def test_three_way_duplicate_names_the_other_two(vault_path):
    edit(vault_path, PUBS, "2025 MAVE mapping.md", "10.1186/s13059-025-03647-x", "10.1093/nar/gkad1040")
    edit(vault_path, PUBS, "2016 SAT1.md", "doi:\n", "doi: 10.1093/nar/gkad1040\n")
    probs = problems(vault_path)
    notes = {"2024 DGIdb 5.0", "2025 MAVE mapping", "2016 SAT1"}
    for note in notes:
        message = one(probs, note + ".md", "doi")
        assert all(other in message for other in notes - {note})
        assert note not in message


def test_duplicate_pmid_and_scholar_id(vault_path):
    edit(vault_path, PUBS, "2025 MAVE mapping.md", "pmid:\n", 'pmid: "37953380"\n')
    edit(vault_path, PUBS, "2025 MAVE mapping.md", "scholar_id:\n", "scholar_id: cwG4QRAAAAAJ:catvrs1\n")
    probs = problems(vault_path)
    assert "2025 MAVE mapping" in one(probs, "2024 DGIdb 5.0.md", "pmid")
    assert "2024 DGIdb 5.0" in one(probs, "2025 MAVE mapping.md", "pmid")
    assert "2026 Cat-VRS preprint" in one(probs, "2025 MAVE mapping.md", "scholar_id")
    assert "2025 MAVE mapping" in one(probs, "2026 Cat-VRS preprint.md", "scholar_id")


def test_duplicate_issn_reports_both_journals(vault_path):
    edit(vault_path, "Journals", "Genome Biology.md", "issn: 1474-760X", "issn: 0305-1048")
    probs = problems(vault_path)
    assert "Nucleic Acids Research" in one(probs, "Genome Biology.md", "issn")
    assert "Genome Biology" in one(probs, "Nucleic Acids Research.md", "issn")
    # Genome Biology's own issn and eissn are equal in the fixture: that is not a duplicate.


def test_duplicate_eissn_reports_both_journals(vault_path):
    edit(vault_path, "Journals", "Genome Biology.md", "eissn: 1474-760X", "eissn: 1362-4962")
    probs = problems(vault_path)
    assert "Nucleic Acids Research" in one(probs, "Genome Biology.md", "eissn")
    assert "Genome Biology" in one(probs, "Nucleic Acids Research.md", "eissn")


def kuzma_two(vault_path):
    (vault_path / "People" / "Kori Kuzma Two.md").write_text("---\naliases:\n  - Kuzma K\nlab_member: true\n---\n# Kori Kuzma Two\n")


def test_ambiguous_alias_in_authors(vault_path):
    kuzma_two(vault_path)
    message = one(problems(vault_path), "2025 MAVE mapping.md", "authors")
    assert "Kuzma K" in message and "Kori Kuzma" in message and "Kori Kuzma Two" in message


def test_ambiguous_alias_in_plain_string_presenter(vault_path):
    kuzma_two(vault_path)
    name = "2026-07-12 Cat-VRS ISMB.md"
    edit(vault_path, PRES, name, '  - "[[Kori Kuzma]]"', "  - Kuzma K")
    message = one(problems(vault_path), name, "presenters")
    assert "Kuzma K" in message and "Kori Kuzma" in message and "Kori Kuzma Two" in message


def test_ambiguous_alias_in_coauthors(vault_path):
    kuzma_two(vault_path)
    edit(vault_path, PRES, CLINVAR, "coauthors: []", "coauthors:\n  - Kuzma K")
    message = one(problems(vault_path), CLINVAR, "coauthors")
    assert "Kuzma K" in message and "Kori Kuzma" in message and "Kori Kuzma Two" in message


def test_unknown_stage(vault_path):
    edit(vault_path, PUBS, "2016 SAT1.md", "stage: Predoctoral", "stage: Graduate")
    assert "Predoctoral | Postdoctoral" in one(problems(vault_path), "2016 SAT1.md", "stage")


def test_cli_exit_codes(vault_path):
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "validate"])
    assert r.exit_code == 1 and "Unframed Meeting.md: type:" in r.output and r.output.rstrip().endswith("2 problems")
    (vault_path / "Conferences" / "Unframed Meeting.md").write_text("---\ntype: conference\nname: Unframed Meeting\nstart: 2026-01-01\nlocation: Virtual\naudience: local\n---\n# Unframed Meeting\n")
    edit(vault_path, PUBS, "2026 Unresolved import.md", "authors: []", "authors:\n  - Wagner AH")
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "validate"])
    assert r.exit_code == 0 and r.output.startswith("OK:")


def test_blank_title_only_for_hackathon_or_workshop(vault_path):
    edit(vault_path, PRES, CLINVAR, "title: Automating somatic cancer submissions to ClinVar with GA4GH genomic knowledge standards", "title:")
    assert one(problems(vault_path), CLINVAR, "title") == "required"
    edit(vault_path, PRES, CLINVAR, "format: invited talk", "format: hackathon")
    assert (CLINVAR, "title") not in problems(vault_path)


def test_single_problem_is_singular(vault_path):
    (vault_path / "Conferences" / "Unframed Meeting.md").unlink()
    r = CliRunner().invoke(main, ["--vault", str(vault_path), "validate"])
    assert r.exit_code == 1 and r.output.rstrip().endswith("\n1 problem")
