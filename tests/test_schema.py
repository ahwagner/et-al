import datetime as dt
from etal.schema import parse_wikilink, Problem

def test_parse_wikilink_forms():
    for raw in ["[[CGC Annual Meeting 2026]]", "[[Conferences/CGC Annual Meeting 2026|CGC 2026]]", "[[CGC Annual Meeting 2026.md]]"]:
        assert parse_wikilink(raw) == "CGC Annual Meeting 2026"
    assert parse_wikilink("Jennifer Bowser") is None

def test_loads_all_types(data):
    assert {j.name for j in data.journals} == {"Nucleic Acids Research", "Genome Biology", "bioRxiv", "Bioinformatics", "PLoS ONE"}
    assert len(data.publications) == 8 and len(data.presentations) == 5 and len(data.honors) == 2
    assert len(data.conferences) == 3  # Unframed Meeting has no frontmatter and is a problem, not a record

def test_links_resolve(data):
    pub = data.by_name["publications"]["2024 DGIdb 5.0"]
    assert pub.journal.abbreviation == "Nucleic Acids Res"
    assert [a.name for a in pub.grants] == ["CIViC U24", "R35"]
    poster = data.by_name["presentations"]["2026-08-05 FUSOR poster"]
    assert poster.event.name == "CGC Annual Meeting 2026"
    assert poster.location == "Satellite venue, Houston, TX" and poster.audience == "national"
    talk = data.by_name["presentations"]["2026-08-03 ClinVar automation CGC"]
    assert talk.location == "Houston, TX"
    assert data.by_name["publications"]["2026 Cat-VRS"].supersedes.note.name == "2026 Cat-VRS preprint"

def test_coercion_of_bare_yaml_values(data):
    pub = data.by_name["publications"]["2013 Exon-level expression"]
    assert pub.pmid == "23500522" and pub.volume == "92"
    assert str(pub.date) == "2013-03-15"
    assert str(data.by_name["publications"]["2026 Unresolved import"].date) == "2026-02"

def test_peer_reviewed_inherits_from_journal(data):
    assert data.by_name["publications"]["2024 DGIdb 5.0"].peer_reviewed is True
    assert data.by_name["publications"]["2026 Cat-VRS preprint"].peer_reviewed is False

def test_presenters_mix_people_and_strings(data):
    p = data.by_name["presentations"]["2026-07 AnyVar research in review"]
    assert p.presenters == ["Jennifer Bowser"]
    q = data.by_name["presentations"]["2026-07-12 Cat-VRS ISMB"]
    assert [x.name for x in q.presenters] == ["Daniel Puthawala", "Kori Kuzma"]

def test_load_problems_name_path_and_field(data):
    msgs = {(p.path.name, p.field) for p in data.problems}
    assert ("Unframed Meeting.md", "type") in msgs
    assert str(sorted(data.problems)[0]).count(": ") >= 2

def test_enumeration_constants():
    from etal import schema
    assert schema.PUBLICATION_FORMATS[0] == "article" and "book chapter" in schema.PUBLICATION_FORMATS
    assert schema.ATTENDANCE == ["in person", "virtual"]
    assert schema.AWARD_ROLES == ["PI", "contact PI", "MPI", "co-I", "OSC", "consultant"]

def test_blank_values_are_none_or_empty(data):
    igm = data.by_name["conferences"]["IGM Research in Review"]
    assert igm.series is None and igm.attended is False
    assert igm.effective_end.last_day() == dt.date(2026, 12, 31)
    cgc = data.by_name["conferences"]["CGC Annual Meeting 2026"]
    assert cgc.attended is True and cgc.end is not None
    pub = data.by_name["publications"]["2026 Unresolved import"]
    assert pub.authors == [] and pub.citations is None and pub.citations_as_of is None and pub.doi is None
    assert data.by_name["journals"]["bioRxiv"].issn is None
    assert data.by_name["journals"]["bioRxiv"].peer_reviewed is False

def test_typed_fields(data):
    pub = data.by_name["publications"]["2013 Exon-level expression"]
    assert pub.citations == 131 and pub.citations_as_of == dt.date(2026, 10, 30)
    assert pub.corresponding == ["Clark AF"] and pub.peer_reviewed is True
    assert data.by_name["publications"]["2016 SAT1"].stage == "Predoctoral"
    kori = data.by_name["people"]["Kori Kuzma"]
    assert kori.aliases == ["Kuzma K", "Kuzma, K", "Kori Kuzma"] and kori.lab_member is True
    r35 = data.by_name["awards"]["R35"]
    assert r35.role == "PI" and str(r35.end) == "2027-06-30"
    assert data.people_by_name["Alex Wagner"].orcid == "0000-0002-2502-8961"

def test_honor_links_and_audience(data):
    h = data.by_name["honors"]["2026-09 GA4GH travel award"]
    assert h.recipient.name == "Daniel Puthawala" and h.audience == "international"
    assert str(h.date) == "2026-09"

def test_fixture_problems_are_exactly_the_unframed_note(data):
    assert [(p.path.name, p.field) for p in data.problems] == [("Unframed Meeting.md", "type")]

def edit(path, old, new):
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))

def problems_by_key(data):
    return {(p.path.name, p.field): p.message for p in data.problems}

def test_unresolved_link_message_names_folder(vault_path):
    from etal import schema
    from etal.config import load_config
    edit(vault_path / "Outputs" / "Publications" / "2024 DGIdb 5.0.md", '"[[R35]]"', '"[[R99]]"')
    edit(vault_path / "Outputs" / "Publications" / "2026 Cat-VRS.md", "[[2026 Cat-VRS preprint]]", "[[Missing preprint]]")
    data = schema.load(load_config(vault_path))
    probs = problems_by_key(data)
    assert probs[("2024 DGIdb 5.0.md", "grants")] == "no note named 'R99' in Awards"
    assert probs[("2026 Cat-VRS.md", "supersedes")] == "no note named 'Missing preprint' in Outputs/Publications"
    assert [a.name for a in data.by_name["publications"]["2024 DGIdb 5.0"].grants] == ["CIViC U24"]

def test_bad_types_become_problems_not_exceptions(vault_path):
    from etal import schema
    from etal.config import load_config
    pub = vault_path / "Outputs" / "Publications" / "2024 DGIdb 5.0.md"
    edit(pub, "citations: 458", "citations: lots")
    edit(pub, "citations_as_of: 2026-10-30", "citations_as_of: yesterday")
    edit(pub, "date: 2024-01-05", "date: someday")
    edit(pub, "co_first: []", "co_first: Wagner AH")
    edit(vault_path / "Journals" / "Genome Biology.md", "peer_reviewed: true", "peer_reviewed: yes please")
    data = schema.load(load_config(vault_path))
    probs = problems_by_key(data)
    for key in ["citations", "citations_as_of", "date", "co_first"]:
        assert ("2024 DGIdb 5.0.md", key) in probs
    assert ("Genome Biology.md", "peer_reviewed") in probs
    rec = data.by_name["publications"]["2024 DGIdb 5.0"]
    assert rec.citations is None and rec.date is None and rec.co_first == []

def test_unquoted_wikilink_gets_a_hint(vault_path):
    from etal import schema
    from etal.config import load_config
    edit(vault_path / "Outputs" / "Publications" / "2025 MAVE mapping.md", 'journal: "[[Genome Biology]]"', "journal: [[Genome Biology]]")
    probs = problems_by_key(schema.load(load_config(vault_path)))
    assert "unquoted" in probs[("2025 MAVE mapping.md", "journal")]

def test_wrong_type_missing_type_and_parse_error(vault_path):
    from etal import schema
    from etal.config import load_config
    edit(vault_path / "Conferences" / "ISMB 2026.md", "type: conference", "type: meeting-series")
    edit(vault_path / "Journals" / "bioRxiv.md", "type: journal\n", "")
    (vault_path / "Awards" / "Broken.md").write_text("---\ntype: award\nfunder: [unclosed\n---\n# Broken\n")
    data = schema.load(load_config(vault_path))
    probs = problems_by_key(data)
    assert "meeting-series" in probs[("ISMB 2026.md", "type")]
    assert "missing" in probs[("bioRxiv.md", "type")]
    assert ("Broken.md", "type") in probs
    assert "ISMB 2026" not in data.by_name["conferences"] and "Broken" not in data.by_name["awards"]
    # the presentation pointing at the dropped conference now fails to resolve
    assert probs[("2026-07-12 Cat-VRS ISMB.md", "event")] == "no note named 'ISMB 2026' in Conferences"

def test_missing_folder_is_empty(tmp_path):
    from etal import schema
    from etal.config import DEFAULT_CONFIG_TEXT, load_config
    (tmp_path / "etal.yaml").write_text(DEFAULT_CONFIG_TEXT)
    data = schema.load(load_config(tmp_path))
    assert data.publications == [] and data.problems == [] and schema.validate(data) == []

def test_problem_str_and_ordering():
    from pathlib import Path
    a = Problem(Path("a.md"), "z", "m"); b = Problem(Path("a.md"), "b", "m"); c = Problem(Path("0.md"), "z", "m")
    assert str(a) == "a.md: z: m"
    assert sorted([a, b, c]) == [c, b, a]

def test_coerce_str():
    import pytest
    from etal.schema import coerce_str
    assert coerce_str(92) == "92" and coerce_str(" x ") == "x"
    assert coerce_str(None) is None and coerce_str("") is None and coerce_str("  ") is None
    with pytest.raises(ValueError):
        coerce_str(True)
    with pytest.raises(ValueError):
        coerce_str(1.5)

def test_people_typed_by_folder(vault_path):
    from etal import schema
    from etal.config import load_config
    # Kori Kuzma has no `type` in the fixture and still loads as a Person.
    data = schema.load(load_config(vault_path))
    kori = data.by_name["people"]["Kori Kuzma"]
    assert "type" not in (kori.note.frontmatter or {})
    assert kori.aliases == ["Kuzma K", "Kuzma, K", "Kori Kuzma"] and kori.lab_member is True
    assert not [p for p in data.problems if p.path.parent.name == "People"]
    # A wrong type is a problem and no record; no frontmatter is a bare Person.
    (vault_path / "People" / "Wrong Type.md").write_text("---\ntype: meeting-series\n---\n# Wrong Type\n")
    (vault_path / "People" / "Bare Person.md").write_text("# Bare Person\n")
    (vault_path / "People" / "Broken Person.md").write_text("---\naliases: [unclosed\n---\n# Broken Person\n")
    data = schema.load(load_config(vault_path))
    probs = problems_by_key(data)
    assert "meeting-series" in probs[("Wrong Type.md", "type")]
    assert ("Broken Person.md", "type") in probs
    assert "Wrong Type" not in data.people_by_name and "Broken Person" not in data.people_by_name
    bare = data.people_by_name["Bare Person"]
    assert bare.aliases == [] and bare.lab_member is False and bare.name == "Bare Person"
    assert not any(p.path.name == "Bare Person.md" for p in data.problems)
