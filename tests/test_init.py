from click.testing import CliRunner
from etal.cli import main
from etal.init_vault import run

def test_init_creates_and_is_idempotent(tmp_path):
    created = run(tmp_path, dry_run=False)
    names = {p.relative_to(tmp_path).as_posix() for p in created}
    assert {"etal.yaml", "Outputs/Publications", "Outputs/Presentations", "Journals", "Conferences", "Honors", "Awards", "People",
            "Outputs/Publications.base", "Outputs/Presentations.base", "People/Alex Wagner.md"} <= names
    assert "Outputs/citation-history.csv" not in names
    assert not (tmp_path / "Outputs" / "citation-history.csv").exists()
    (tmp_path / "etal.yaml").write_text("custom: true\n")
    assert run(tmp_path, dry_run=False) == []
    assert (tmp_path / "etal.yaml").read_text() == "custom: true\n"

def test_base_files_follow_obsidian_format(tmp_path):
    run(tmp_path, dry_run=False)
    text = (tmp_path / "Outputs" / "Presentations.base").read_text()
    assert 'file.inFolder("Outputs/Presentations")' in text
    for col in ["date", "format", "attendance", "event", "presenters", "audience", "grants"]:
        assert f"- {col}" in text
    assert "direction: DESC" in text

def test_dry_run_writes_nothing(tmp_path):
    r = CliRunner().invoke(main, ["--vault", str(tmp_path), "init", "--dry-run"])
    assert r.exit_code == 0 and "etal.yaml" in r.output and not (tmp_path / "etal.yaml").exists()

def test_dry_run_reports_each_item_and_real_run_reports_created(tmp_path):
    dry = CliRunner().invoke(main, ["--vault", str(tmp_path), "init", "--dry-run"])
    assert "Would create etal.yaml" in dry.output
    assert "Would create People/Alex Wagner.md" in dry.output
    real = CliRunner().invoke(main, ["--vault", str(tmp_path), "init"])
    assert real.exit_code == 0 and "Created etal.yaml" in real.output
    assert (tmp_path / "People" / "Alex Wagner.md").is_file()
    again = CliRunner().invoke(main, ["--vault", str(tmp_path), "init"])
    assert again.output.strip() == "Nothing to do"

def test_init_leaves_existing_files_alone(tmp_path):
    (tmp_path / "People").mkdir()
    (tmp_path / "People" / "Alex Wagner.md").write_text("mine\n")
    created = run(tmp_path, dry_run=False)
    assert tmp_path / "People" / "Alex Wagner.md" not in created
    assert (tmp_path / "People" / "Alex Wagner.md").read_text() == "mine\n"

def test_alex_note_has_identity_fields(tmp_path):
    run(tmp_path, dry_run=False)
    text = (tmp_path / "People" / "Alex Wagner.md").read_text()
    assert text.startswith("---\n") and "orcid: 0000-0002-2502-8961" in text
    assert "scholar_id: cwG4QRAAAAAJ" in text and "lab_member: true" in text
    assert "\n# Alex Wagner" in text and "type:" not in text

def test_initialized_vault_validates(tmp_path):
    run(tmp_path, dry_run=False)
    r = CliRunner().invoke(main, ["--vault", str(tmp_path), "validate"])
    assert r.exit_code == 0, r.output
