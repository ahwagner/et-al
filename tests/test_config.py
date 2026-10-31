import datetime as dt
import pytest
from etal.config import Config, ConfigError, DEFAULT_CONFIG_TEXT, load_config, find_vault, parse_wikilink
from etal.dates import PartialDate

def test_default_config_loads(tmp_path):
    (tmp_path / "etal.yaml").write_text(DEFAULT_CONFIG_TEXT)
    cfg = load_config(tmp_path)
    assert cfg.self_name == "Alex Wagner"
    assert cfg.scholar_profile == "cwG4QRAAAAAJ"
    assert [s.name for s in cfg.career_stages] == ["Predoctoral", "Postdoctoral", "Nationwide Children's Hospital"]
    assert cfg.career_stages[0].until == dt.date(2014, 12, 31)
    assert cfg.career_stages[2].until is None
    assert cfg.merge_superseded is False
    assert cfg.folder("publications") == tmp_path / "Outputs" / "Publications"
    assert cfg.history_path == tmp_path / "Outputs" / "citation-history.csv"

@pytest.mark.parametrize("raw,stage", [
    ("2013-05", "Predoctoral"), ("2014-12-31", "Predoctoral"), ("2015-01-01", "Postdoctoral"),
    ("2020-08-02", "Postdoctoral"), ("2020-08-03", "Nationwide Children's Hospital"), ("2026", "Nationwide Children's Hospital"),
])
def test_stage_for(tmp_path, raw, stage):
    (tmp_path / "etal.yaml").write_text(DEFAULT_CONFIG_TEXT)
    assert load_config(tmp_path).stage_for(PartialDate.parse(raw)) == stage

def test_missing_self_is_named(tmp_path):
    (tmp_path / "etal.yaml").write_text("scholar_profile: x\ncareer_stages:\n  - name: Only\n")
    with pytest.raises(ConfigError, match="self"):
        load_config(tmp_path)

def test_find_vault_prefers_cli_then_env_then_cwd(tmp_path, monkeypatch):
    (tmp_path / "etal.yaml").write_text(DEFAULT_CONFIG_TEXT)
    assert find_vault(str(tmp_path)) == tmp_path
    monkeypatch.setenv("ETAL_VAULT", str(tmp_path))
    assert find_vault(None) == tmp_path
    monkeypatch.delenv("ETAL_VAULT")
    monkeypatch.chdir(tmp_path)
    assert find_vault(None) == tmp_path
    monkeypatch.chdir(tmp_path.parent)
    with pytest.raises(ConfigError):
        find_vault(None)

@pytest.mark.parametrize("raw", ["[[Name]]", "[[Folder/Name]]", "[[Name|display]]", "[[Name.md]]"])
def test_parse_wikilink(raw):
    assert parse_wikilink(raw) == "Name"

def test_parse_wikilink_without_brackets_is_none():
    assert parse_wikilink("Name") is None
