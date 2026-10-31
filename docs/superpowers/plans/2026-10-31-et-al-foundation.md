# et-al Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `etal` command line tool that reads Alex's Obsidian vault as its only database, validates the note schema, syncs Google Scholar citation counts, and renders the citation report and the quarterly outputs note.

**Architecture:** A Python package where `vault.py` is the only module touching the file system; everything else works on in-memory records loaded by `schema.py`, which also owns link resolution and inheritance of defaults. Name matching lives only in `people.py`. The Scholar sync separates network fetch from pure match and apply so tests use recorded responses. Reports and sync are exercised against a fixture vault committed under `tests/fixtures/vault`.

**Tech Stack:** Python 3.12, `uv` for packaging and environments, `click` for the CLI, `ruamel.yaml` in round-trip mode for frontmatter (preserves key order and quoting), `rich` for terminal tables, `scholarly` for the Scholar profile, `pytest`.

**Spec:** `docs/superpowers/specs/2026-10-30-et-al-foundation-design.md`

## Global Constraints

- Python 3.12. Package name `etal`, source under `src/etal/`, console script `etal`.
- The tool never runs git, never deletes or renames a note, never modifies a note body.
- Frontmatter is rewritten with the original key order; new keys are appended at the end; quoting style of untouched values is preserved. `pmid` and `volume` are strings.
- Wikilinks in properties are written as `"[[Note name]]"` (double quoted). Reading accepts `[[Folder/Name]]`, `[[Name|display]]`, and `[[Name.md]]` and resolves to `Name`.
- Dates are ISO. `YYYY-MM-DD`, `YYYY-MM`, and `YYYY` all parse; month-only prints "day not recorded" in reports.
- Every command takes `--vault PATH`, defaulting to `ETAL_VAULT`, then the current directory if it holds `etal.yaml`. Writer commands take `--dry-run`.
- Every command except `init` runs validation first and stops with exit code 1 on any problem, printing one line per problem as `path: field: message` then a count. Operational failures (network, the daily sync guard) exit 2.
- No test touches the network. The Scholar fetch is wrapped so tests inject recorded responses.
- Property names are exactly the spec's: `format` (not kind), `attendance` (not modality), `sources`, `stage`.
- Enumerations, verbatim from the spec:
  - publication `format`: article | preprint | review | book chapter | white paper | dataset | software | abstract | other
  - publication `status`: published | accepted | submitted | preprint | in preparation
  - presentation `format`: poster | invited talk | platform | lightning talk | workshop | panel | course lecture | hackathon | consortium update | other
  - presentation `attendance`: in person | virtual
  - `audience` (conference, presentation, honor): international | national | regional | institutional | local
  - honor `result`: won | nominated | finalist
  - award `role`: PI | contact PI | MPI | co-I | OSC | consultant

## Review Focus

1. A note whose frontmatter has no `type`, or a `type` the folder does not expect (a stray `type: meeting-series` in `Conferences/`): validate must report `type` on that note rather than crash or silently skip it. Test in Task 6.
2. YAML's own typing of bare values: an unquoted `pmid: 37953380` loads as an int, `date: 2016` as an int, `date: 2024-01-05` as a `datetime.date`, `volume: 52` as an int. The loader must coerce all of these without an error and without changing the file. Tests in Tasks 2 and 4.
3. Wikilinks written with a folder prefix or a display alias (`[[Conferences/CGC Annual Meeting 2026|CGC 2026]]`) must resolve to the same note as `[[CGC Annual Meeting 2026]]`. Test in Task 4.
4. A publication with `authors: []` (an unresolved import) must validate with a problem on `authors`, and the flag derivation must return all false rather than raise on `authors[0]`. Test in Task 5.
5. A Scholar work missing `pub_year` or `num_citations`, or a profile with zero publications: sync must report, not crash, and leave notes untouched. Test in Task 11.

---

## File map

```
pyproject.toml                      package metadata, deps, console script, pytest config
README.md                           replace the one-line README with install and usage
src/etal/__init__.py                __version__
src/etal/cli.py                     click group and subcommands; no logic
src/etal/config.py                  Config, Stage, load_config, find_vault, default config text
src/etal/dates.py                   PartialDate
src/etal/vault.py                   Note, read/write frontmatter, folder listing, atomic CSV append
src/etal/schema.py                  record dataclasses, VaultData, load(), validate(), Problem, wikilink parsing, enumerations
src/etal/people.py                  AliasIndex, AuthorFlags, derive flags
src/etal/render.py                  markdown_table, csv_text, nlm_citation, presentation_line
src/etal/reports/__init__.py
src/etal/reports/citations.py       build_citation_report, render_citations_markdown, render_citations_csv
src/etal/reports/quarter.py         Quarter, build_quarter_note, render_quarter_note
src/etal/sync/__init__.py
src/etal/sync/scholar.py            ScholarWork, normalize_title, fetch, match, apply, history
src/etal/init_vault.py              init command logic, base file and default note text
tests/conftest.py                   fixture_vault (copied to tmp_path), load helpers
tests/fixtures/vault/               the fixture vault (Task 4)
tests/fixtures/scholar/profile.json recorded Scholar works (Task 11)
tests/golden/                       golden report outputs (Tasks 9, 10)
tests/test_*.py                     one file per module
```

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `src/etal/__init__.py`, `src/etal/cli.py`, `tests/test_cli.py`, `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Produces: `etal.cli.main` (click group). `etal.__version__ = "0.1.0"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from click.testing import CliRunner
from etal.cli import main

def test_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL (module `etal` not found)

- [ ] **Step 3: Create `pyproject.toml`**

`[project]` name `et-al`, version `0.1.0`, `requires-python = ">=3.12"`, dependencies `click>=8.1`, `ruamel.yaml>=0.18`, `rich>=13`, `scholarly>=1.7`. `[project.scripts] etal = "etal.cli:main"`. Build backend `hatchling` with `packages = ["src/etal"]`. `[dependency-groups] dev = ["pytest>=8"]`. `[tool.pytest.ini_options] testpaths = ["tests"]`.

- [ ] **Step 4: Create `src/etal/__init__.py` and `src/etal/cli.py`**

`cli.py`: `@click.group() @click.version_option(__version__) @click.option("--vault", type=click.Path(), envvar="ETAL_VAULT", default=None) @click.pass_context def main(ctx, vault)` storing `vault` in `ctx.obj`. No subcommands yet.

- [ ] **Step 5: Add `.gitignore`** with `.venv/`, `__pycache__/`, `*.egg-info/`, `dist/`, `.pytest_cache/`.

- [ ] **Step 6: Run test to verify it passes**

Run: `uv sync && uv run pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 7: Replace `README.md`** with: what the tool is (two sentences from the spec's Purpose), install (`uv tool install .` or `uv sync`), the `ETAL_VAULT` variable, the five commands with one line each, and links to the spec and `docs/wheatley-migration.md`.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock .gitignore README.md src/etal tests/test_cli.py
git commit -m "Scaffold etal package with click entry point"
```

---

### Task 2: PartialDate and configuration

**Files:**
- Create: `src/etal/dates.py`, `src/etal/config.py`, `tests/test_dates.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `dates.PartialDate(year: int, month: int | None = None, day: int | None = None)` with `PartialDate.parse(value: str | int | datetime.date | datetime.datetime) -> PartialDate` (raises `ValueError` on anything else or on an unparsable string), `precision -> Literal["year", "month", "day"]`, `__str__` giving `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`, `first_day() -> datetime.date` (missing month and day become 1), `last_day() -> datetime.date`, ordering by `first_day()` then precision (less precise first), `day_recorded -> bool`.
  - `config.Stage(name: str, until: datetime.date | None)`
  - `config.Config(root: Path, self_name: str, scholar_profile: str, career_stages: list[Stage], merge_superseded: bool, folders: dict[str, str])` with `folder(key) -> Path` (absolute), `history_path -> Path`, `stage_for(d: PartialDate) -> str`, `stage_names -> list[str]`.
  - `config.load_config(root: Path) -> Config` (raises `ConfigError` naming the field when `self`, `scholar_profile`, or `career_stages` is missing, when a stage has no `name`, or when any stage but the last has no `until`).
  - `config.find_vault(cli_value: str | None) -> Path` (CLI value, else `ETAL_VAULT`, else cwd if it holds `etal.yaml`, else `ConfigError`).
  - `config.DEFAULT_CONFIG_TEXT: str`, the spec's `etal.yaml` example verbatim, including comments.
  - `config.parse_wikilink(value: str) -> str | None`: `[[Name]]`, `[[Folder/Name]]`, `[[Name|display]]`, `[[Name.md]]` all give `Name`; a string without `[[ ]]` gives `None`. `self_name` is `parse_wikilink(self)`. `schema.py` (Task 4) re-exports it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dates.py
import datetime as dt
import pytest
from etal.dates import PartialDate

@pytest.mark.parametrize("raw,expected", [
    ("2024-01-05", "2024-01-05"), ("2026-07", "2026-07"), ("2016", "2016"),
    (2016, "2016"), (dt.date(2024, 1, 5), "2024-01-05"),
    (dt.datetime(2024, 1, 5, 10, 0), "2024-01-05"),
])
def test_parse_and_str(raw, expected):
    assert str(PartialDate.parse(raw)) == expected

def test_precision_and_day_recorded():
    assert PartialDate.parse("2026-07").precision == "month"
    assert PartialDate.parse("2026-07").day_recorded is False
    assert PartialDate.parse("2026-07-12").day_recorded is True

def test_month_only_sorts_before_days_in_month():
    assert PartialDate.parse("2026-07") < PartialDate.parse("2026-07-01")

def test_first_and_last_day():
    assert PartialDate.parse("2026-07").first_day() == dt.date(2026, 7, 1)
    assert PartialDate.parse("2026-07").last_day() == dt.date(2026, 7, 31)
    assert PartialDate.parse("2016").last_day() == dt.date(2016, 12, 31)

@pytest.mark.parametrize("bad", ["July 2026", "2026-13", "", None, 3.5])
def test_rejects(bad):
    with pytest.raises(ValueError):
        PartialDate.parse(bad)
```

```python
# tests/test_config.py
import datetime as dt
import pytest
from etal.config import Config, ConfigError, DEFAULT_CONFIG_TEXT, load_config, find_vault
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dates.py tests/test_config.py -v`
Expected: FAIL (modules not found)

- [ ] **Step 3: Implement `src/etal/dates.py`**

`PartialDate` as a frozen dataclass with `order=False` and explicit `__lt__` on `(first_day(), precision_rank)` where year < month < day rank. `parse` handles `datetime.datetime` before `datetime.date` (subclass), int as year, str by regex `^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$` with range checks via `datetime.date`.

- [ ] **Step 4: Implement `src/etal/config.py`**

Load with `ruamel.yaml.YAML(typ="safe")`. `folders` merge the spec defaults with any overrides. `stage_for` walks stages in order and returns the first whose `until` is `None` or `>= d.first_day()`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_dates.py tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/etal/dates.py src/etal/config.py tests/test_dates.py tests/test_config.py
git commit -m "Add PartialDate and etal.yaml configuration"
```

---

### Task 3: Vault file access

**Files:**
- Create: `src/etal/vault.py`, `tests/test_vault.py`

**Interfaces:**
- Produces:
  - `vault.Note(path: Path, name: str, frontmatter: CommentedMap | None, body: str, parse_error: str | None)`; `name` is the basename without `.md`.
  - `vault.read_note(path: Path) -> Note`. A file with no leading `---` gives `frontmatter=None, parse_error=None, body=<whole file>`. A file whose YAML fails to parse gives `frontmatter=None, parse_error=<message>`.
  - `vault.read_folder(folder: Path) -> list[Note]`: the `*.md` files directly in `folder`, sorted by name; an absent folder gives `[]`.
  - `vault.write_frontmatter(note: Note, updates: dict[str, object]) -> None`: sets each key (existing keys in place, new keys appended), writes the file as `---\n<yaml>\n---\n<body>`; raises `ValueError` if `note.frontmatter is None`.
  - `vault.write_text(path: Path, text: str) -> None` and `vault.exists(path) -> bool`.
  - `vault.append_csv_rows(path: Path, header: list[str], rows: list[list[str]]) -> None`: creates with header if absent; atomic (temp file in the same directory, then `os.replace`).
  - `vault.read_csv_rows(path: Path) -> list[dict[str, str]]` (empty list if absent).
  - `vault.split_frontmatter(text: str) -> tuple[str | None, str]` and `vault.YAML` (a configured `ruamel.yaml.YAML(typ="rt")` with `preserve_quotes=True`, `width=4096`, `indent(mapping=2, sequence=4, offset=2)`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_vault.py
import datetime as dt
from pathlib import Path
from etal.vault import read_note, read_folder, write_frontmatter, append_csv_rows, read_csv_rows

SAMPLE = '''---
type: publication
title: "DGIdb 5.0: rebuilding"
date: 2024-01-05
pmid: "37953380"
grants:
  - "[[CIViC U24]]"
---
# DGIdb 5.0

Body text stays.
'''

def test_read_note(tmp_path):
    p = tmp_path / "2024 DGIdb 5.0.md"; p.write_text(SAMPLE)
    n = read_note(p)
    assert n.name == "2024 DGIdb 5.0"
    assert n.frontmatter["type"] == "publication"
    assert n.frontmatter["date"] == dt.date(2024, 1, 5)
    assert n.frontmatter["pmid"] == "37953380"
    assert n.body == "# DGIdb 5.0\n\nBody text stays.\n"
    assert n.parse_error is None

def test_note_without_frontmatter(tmp_path):
    p = tmp_path / "Plain.md"; p.write_text("# Epic\n- Follow up\n")
    n = read_note(p)
    assert n.frontmatter is None and n.parse_error is None and n.body.startswith("# Epic")

def test_bad_yaml_reports_error(tmp_path):
    p = tmp_path / "Bad.md"; p.write_text("---\ntitle: [unclosed\n---\nbody\n")
    n = read_note(p)
    assert n.frontmatter is None and n.parse_error

EXPECTED_AFTER_SYNC = '''---
type: publication
title: "DGIdb 5.0: rebuilding"
date: 2024-01-05
pmid: "37953380"
grants:
  - "[[CIViC U24]]"
citations: 458
citations_as_of: 2026-10-30
---
# DGIdb 5.0

Body text stays.
'''

def test_round_trip_preserves_everything_else(tmp_path):
    p = tmp_path / "n.md"; p.write_text(SAMPLE)
    n = read_note(p)
    write_frontmatter(n, {"citations": 458, "citations_as_of": dt.date(2026, 10, 30)})
    assert p.read_text() == EXPECTED_AFTER_SYNC

def test_update_existing_key_keeps_position(tmp_path):
    p = tmp_path / "n.md"; p.write_text(SAMPLE)
    n = read_note(p)
    write_frontmatter(n, {"title": "New title"})
    lines = p.read_text().splitlines()
    assert lines[1] == "type: publication" and lines[2] == "title: New title"

def test_read_folder_sorted_and_missing(tmp_path):
    (tmp_path / "b.md").write_text("x"); (tmp_path / "a.md").write_text("y"); (tmp_path / "c.txt").write_text("z")
    assert [n.name for n in read_folder(tmp_path)] == ["a", "b"]
    assert read_folder(tmp_path / "nope") == []

def test_csv_append_is_cumulative(tmp_path):
    p = tmp_path / "h.csv"
    append_csv_rows(p, ["as_of", "note", "scholar_id", "citations"], [["2026-10-30", "2024 DGIdb 5.0", "x:1", "458"]])
    append_csv_rows(p, ["as_of", "note", "scholar_id", "citations"], [["2026-10-31", "2024 DGIdb 5.0", "x:1", "460"]])
    rows = read_csv_rows(p)
    assert [r["citations"] for r in rows] == ["458", "460"]
    assert p.read_text().splitlines()[0] == "as_of,note,scholar_id,citations"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_vault.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement `src/etal/vault.py`**

`split_frontmatter`: text must start with `---\n`; the closing fence is the next line equal to `---`; return the YAML between and the body after the fence line. Dump with the shared `YAML` instance into a `StringIO`; strip a trailing `...\n` document end marker if ruamel adds one. Write files with `encoding="utf-8"` and `newline="\n"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_vault.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/etal/vault.py tests/test_vault.py
git commit -m "Add vault note reading, frontmatter round-trip, and atomic CSV append"
```

---

### Task 4: Fixture vault and schema loading

**Files:**
- Create: `tests/fixtures/vault/**` (below), `tests/conftest.py`, `src/etal/schema.py`, `tests/test_schema.py`

**Interfaces:**
- Consumes: `vault.read_folder`, `vault.Note`, `config.Config`, `config.parse_wikilink`, `dates.PartialDate`.
- Produces:
  - `schema.parse_wikilink`: re-export of `config.parse_wikilink`.
  - `schema.Problem(path: Path, field: str, message: str)` with `__str__` = `f"{path}: {field}: {message}"`; sorted by `(path, field)`.
  - Record dataclasses, each with `note: Note` plus typed fields (blank or missing property gives `None` or `[]`):
    - `Journal(name, abbreviation, issn, eissn, publisher, url, peer_reviewed: bool | None, nlm_id)`
    - `Conference(name, series, start: PartialDate | None, end: PartialDate | None, location, audience, organizer, url, attended: bool)`; `effective_end` = `end or start`.
    - `Person(name, aliases: list[str], orcid, scholar_id, lab_member: bool, tenure: list[dict])`; `name` is the note name.
    - `Award(name, grant_number, funder, role, start, end)`
    - `Publication(title, format, status, date, journal_link: str | None, journal: Journal | None, volume, issue, pages, authors: list[str], co_first, corresponding, senior, peer_reviewed_own: bool | None, doi, pmid, pmcid, url, scholar_id, citations: int | None, citations_as_of: datetime.date | None, grant_links: list[str], grants: list[Award], supersedes_link, supersedes: Publication | None, stage, sources: list[str], notes)`; property `peer_reviewed -> bool` (own, else journal's, else `False`).
    - `Presentation(title, date, format, attendance, event_link, event: Conference | None, session, location_own, audience_own, presenter_links: list[str], presenters: list[Person | str], coauthors, grant_links, grants, slides, poster, abstract_doi, sources, notes)`; properties `location` and `audience` (own, else event's, else `None`).
    - `Honor(name, date, result, venue, event_link, event, audience_own, recipient_link, recipient: Person | None, related_link, related: Publication | Presentation | None, sources, notes)`; property `audience`.
  - `schema.VaultData(config, journals, conferences, people, awards, publications, presentations, honors, problems: list[Problem])` with `by_name[folder_key][note_name]` index and `people_by_name`.
  - `schema.load(config: Config) -> VaultData`: reads every configured folder, builds records, resolves links, collects load-time problems (parse errors, missing or wrong `type`, type coercion failures, unresolved links). Never raises on bad data.
  - `schema.validate(data: VaultData) -> list[Problem]`: `data.problems` plus the rule checks of Task 6. In this task it returns `data.problems` only.
  - Enumeration constants: `PUBLICATION_FORMATS`, `PUBLICATION_STATUSES`, `PRESENTATION_FORMATS`, `ATTENDANCE`, `AUDIENCES`, `HONOR_RESULTS`, `AWARD_ROLES` (values verbatim from Global Constraints).
  - `schema.coerce_str(value) -> str | None` (int to str, `None` and `""` to `None`, strips).

- [ ] **Step 1: Create the fixture vault**

`tests/fixtures/vault/etal.yaml` = `DEFAULT_CONFIG_TEXT`. Notes, each with the spec's properties (write them in full; values below are what tests assert):

- `Journals/Nucleic Acids Research.md` (abbreviation `Nucleic Acids Res`, issn `0305-1048`, peer_reviewed true), `Journals/Genome Biology.md` (`Genome Biol`, peer_reviewed true), `Journals/bioRxiv.md` (`bioRxiv`, peer_reviewed false), `Journals/Bioinformatics.md` (`Bioinformatics`, peer_reviewed true), `Journals/PLoS ONE.md` (`PLoS One`, true).
- `Conferences/CGC Annual Meeting 2026.md` (series `CGC Annual Meeting`, start 2026-08-01, end 2026-08-05, location `Houston, TX`, audience national, attended true), `Conferences/IGM Research in Review.md` (name `IGM Research in Review`, no series, start 2026-01-01, end 2026-12-31 because the series meets monthly all year, location `Virtual`, audience institutional, no `attended`), `Conferences/ISMB 2026.md` (series `ISMB`, start 2026-07-12, end 2026-07-16, location `Washington, DC`, audience international, attended true), `Conferences/Unframed Meeting.md` with no frontmatter at all (body `# Unframed Meeting`).
- `People/Alex Wagner.md` (aliases `Wagner AH`, `Wagner A`, `Alex Wagner`; lab_member true; orcid `0000-0002-2502-8961`), `People/Kori Kuzma.md` (aliases `Kuzma K`, `Kuzma, K`, `Kori Kuzma`; lab_member true; also `things_tag: Kori Kuzma`), `People/Matt Cannon.md` (aliases `Cannon M`, `Matt Cannon`; lab_member true), `People/Daniel Puthawala.md` (aliases `Puthawala D`, `Puthawala, D`, `Daniel Puthawala`; lab_member true).
- `Awards/R35.md` (type award, status active, stage "No-cost extension through June 30, 2027.", grant_number `R35HG011949`, funder NHGRI, role PI, start 2021-09-08, end 2027-06-30), `Awards/CIViC U24.md` (grant_number `U24CA305456`, funder NCI, role MPI, start 2024-09-01, end 2029-08-31), `Awards/R03.md` (grant_number `R03HG014803`, funder NHGRI, role `contact PI`, start 2026-05-01, end 2028-04-30).
- `Outputs/Publications/2013 Exon-level expression.md`: title `Exon-level expression profiling of ocular tissues`, format article, status published, date 2013-03-15, journal `[[PLoS ONE]]`, authors `Wagner AH, Anand VN, Wang WH, Chatterton JE, Sun D, Shepard AR, Jacobson N, Pang IH, Deluca AP, Casavant TL, Scheetz TE, Mullins RF, Braun TA, Clark AF`, corresponding `Clark AF`, citations 131, citations_as_of 2026-10-30, pmid "23500522" unquoted as `pmid: 23500522` (Review Focus 2), volume unquoted `volume: 92`.
- `Outputs/Publications/2016 SAT1.md`: title `Whole-gene sequencing investigation of SAT1 in attempted suicide`, date 2016-03-01, journal `[[PLoS ONE]]`, authors `Vasiliou V, ..., Wagner AH, ..., Potash JB` (Wagner neither first nor last; use six names), stage `Predoctoral`, citations 11.
- `Outputs/Publications/2024 DGIdb 5.0.md`: exactly the spec's example (format article, status published, date 2024-01-05, the fourteen authors, corresponding `Wagner AH`, doi, pmid "37953380", pmcid, citations 458, citations_as_of 2026-10-30, grants `[[CIViC U24]]`, `[[R35]]`, sources two lines).
- `Outputs/Publications/2025 MAVE mapping.md`: title `Mapping MAVE data for use in human genomics applications`, date 2025-06-25, journal `[[Genome Biology]]`, authors `Arbesfeld JA, Da EY, Stevenson JS, Kuzma K, Rubin AF, Wagner AH`, co_first `[]`, corresponding `[]`, senior `[]` (Wagner last), citations 10, doi `10.1186/s13059-025-03647-x`, grants `[[R35]]`.
- `Outputs/Publications/2026 Cat-VRS preprint.md`: title `The GA4GH Categorical Variation Representation Specification: A Unified Computational Framework for Reasoning over Genomic Variant Categories`, format preprint, status preprint, date 2026-04-30, journal `[[bioRxiv]]`, authors `Puthawala D, Reardon B, Wagner AH`, citations 3, scholar_id `cwG4QRAAAAAJ:catvrs1`.
- `Outputs/Publications/2026 Cat-VRS.md`: the same title, format article, status accepted, date 2026-09-28, journal `[[Bioinformatics]]`, same authors, supersedes `[[2026 Cat-VRS preprint]]`, citations 2.
- `Outputs/Publications/2026 Druggable genome LLM.md`: title `Searching the druggable genome using large language models`, date 2026-08-22, journal `[[Bioinformatics]]`, volume "42", issue "9", pages `btag632`, authors `Schimmelpfennig L, Cannon M, Cody Q, McMichael J, Coffman AC, Kiwala S, Krysiak K, Wagner AH, Griffith M, Griffith OL`, doi `10.1093/bioinformatics/btag632`, pmid "42631692", pmcid `PMC13544961`, citations 1, grants `[[CIViC U24]]`.
- `Outputs/Publications/2026 Unresolved import.md`: title `A paper the import could not resolve`, format article, status published, date 2026-02, journal `[[PLoS ONE]]`, `authors: []` (Review Focus 4).
- `Outputs/Presentations/2026-08-03 ClinVar automation CGC.md`: the spec's example (format `invited talk`, attendance `in person`, event `[[CGC Annual Meeting 2026]]`, presenters `[[Alex Wagner]]`, grants `[[CIViC U24]]`, slides URL).
- `Outputs/Presentations/2026-08-05 FUSOR poster.md`: title `Standardizing fusion calls in a computable format with FUSOR`, date 2026-08-05, format poster, attendance `in person`, event `[[Conferences/CGC Annual Meeting 2026|CGC 2026]]` (Review Focus 3), presenters `[[Daniel Puthawala]]`, location `Satellite venue, Houston, TX` (own override).
- `Outputs/Presentations/2026-07 AnyVar research in review.md`: title `AnyVar and AnyVLM`, date `2026-07`, format `lightning talk`, attendance virtual, event `[[IGM Research in Review]]`, presenters `Jennifer Bowser` (plain string, no note).
- `Outputs/Presentations/2026-07-12 Cat-VRS ISMB.md`: title `Scalable Representation of Categorical Genomic Variation Using Cat-VRS`, date 2026-07-12, format platform, attendance `in person`, event `[[ISMB 2026]]`, presenters `[[Daniel Puthawala]]`, `[[Kori Kuzma]]`, grants `[[R35]]`.
- `Outputs/Presentations/2026-06-20 Prior quarter talk.md`: title `A talk from June`, date 2026-06-20, format `invited talk`, attendance virtual, event `[[IGM Research in Review]]`, presenters `[[Alex Wagner]]`.
- `Honors/2024-12-02 BSGP Distinguished Research Mentor Award.md`: the spec's example.
- `Honors/2026-09 GA4GH travel award.md`: name `GA4GH travel award`, date `2026-09`, result won, venue `GA4GH`, audience international, recipient `[[Daniel Puthawala]]`.
- `Outputs/2026-Q2 outputs.md`: frontmatter `type: outputs`, `quarter: 2026-Q2`; body with a `## Presentations` section containing one line that includes `A talk from June` (so lookback finds it already reported).

- [ ] **Step 2: Create `tests/conftest.py`**

```python
import shutil
from pathlib import Path
import pytest
from etal.config import load_config
from etal import schema

FIXTURE = Path(__file__).parent / "fixtures" / "vault"

@pytest.fixture
def vault_path(tmp_path):
    dest = tmp_path / "vault"
    shutil.copytree(FIXTURE, dest)
    return dest

@pytest.fixture
def data(vault_path):
    return schema.load(load_config(vault_path))
```

- [ ] **Step 3: Write the failing tests**

```python
# tests/test_schema.py
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
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_schema.py -v`
Expected: FAIL (module not found)

- [ ] **Step 5: Implement `src/etal/schema.py`**

`load` does two passes: build every record from its note with links kept as strings, then resolve links across folders (`journal` in journals, `event` in conferences, `grants` in awards, `presenters` and `recipient` in people, `supersedes` and `related` in publications then presentations). An unresolved link is a `Problem(path, field, f"no note named '{name}' in {folder}")` where `folder` is the configured relative folder (`Awards`, `Outputs/Publications`). A note in a folder whose `type` is missing or is not the folder's type gets `Problem(path, "type", ...)` and no record. `citations` must be an int (`Problem` if not); `citations_as_of` a date. Bool fields accept YAML booleans only.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest -v`
Expected: PASS (all files)

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures tests/conftest.py src/etal/schema.py src/etal/config.py tests/test_schema.py
git commit -m "Add fixture vault and schema loading with link resolution"
```

---

### Task 5: People and authorship flags

**Files:**
- Create: `src/etal/people.py`, `tests/test_people.py`

**Interfaces:**
- Consumes: `schema.Person`, `schema.Publication`.
- Produces:
  - `people.normalize_name(s: str) -> str`: strip, casefold, collapse whitespace, drop trailing periods.
  - `people.AliasIndex.build(people: list[Person]) -> AliasIndex`; `resolve(printed: str) -> Person | None` (exactly one match), `candidates(printed) -> list[Person]` (all matches, for validation), `is_person(printed, person) -> bool`.
  - `people.AuthorFlags(first: bool, senior_or_corresponding: bool, peer_reviewed: bool)` with property `first_or_corresponding_peer_reviewed -> bool`.
  - `people.author_flags(pub: Publication, person: Person, index: AliasIndex) -> AuthorFlags` implementing the spec's three rules; empty `authors` gives all false except `peer_reviewed`.
  - `people.is_author(pub, person, index) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_people.py
from etal.people import AliasIndex, author_flags, is_author, normalize_name

def test_normalize_name():
    assert normalize_name("  Wagner,  AH. ") == "wagner, ah"

def test_resolve_through_aliases(data):
    idx = AliasIndex.build(data.people)
    assert idx.resolve("Kuzma, K").name == "Kori Kuzma"
    assert idx.resolve("wagner ah").name == "Alex Wagner"
    assert idx.resolve("Griffith OL") is None

def test_flags_last_author_is_senior(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2025 MAVE mapping"], alex, idx)
    assert (f.first, f.senior_or_corresponding, f.peer_reviewed, f.first_or_corresponding_peer_reviewed) == (False, True, True, True)

def test_flags_first_author_not_corresponding(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2013 Exon-level expression"], alex, idx)
    assert (f.first, f.senior_or_corresponding) == (True, False)

def test_flags_corresponding_and_last(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2024 DGIdb 5.0"], alex, idx)
    assert (f.first, f.senior_or_corresponding) == (False, True)

def test_flags_middle_author(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2016 SAT1"], alex, idx)
    assert (f.first, f.senior_or_corresponding, f.first_or_corresponding_peer_reviewed) == (False, False, False)

def test_flags_preprint_not_peer_reviewed(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    f = author_flags(data.by_name["publications"]["2026 Cat-VRS preprint"], alex, idx)
    assert f.senior_or_corresponding and not f.peer_reviewed and not f.first_or_corresponding_peer_reviewed

def test_empty_authors_do_not_raise(data):
    idx = AliasIndex.build(data.people); alex = idx.resolve("Alex Wagner")
    pub = data.by_name["publications"]["2026 Unresolved import"]
    assert not is_author(pub, alex, idx)
    f = author_flags(pub, alex, idx)
    assert (f.first, f.senior_or_corresponding) == (False, False)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_people.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `src/etal/people.py`**

The index maps `normalize_name(alias)` and `normalize_name(person.name)` to a list of people.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_people.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/etal/people.py tests/test_people.py
git commit -m "Add alias index and authorship flag derivation"
```

---

### Task 6: Validation rules and the `validate` command

**Files:**
- Modify: `src/etal/schema.py` (`validate`), `src/etal/cli.py`
- Create: `tests/test_validate.py`

**Interfaces:**
- Consumes: `schema.load`, `people.AliasIndex`.
- Produces:
  - `schema.validate(data: VaultData) -> list[Problem]`, sorted, covering every rule in the spec's `etal validate` section plus required properties per type.
  - `cli.run_validation(vault: Path) -> tuple[Config, VaultData]`: loads config and data, prints problems and count, calls `sys.exit(1)` if any. Every later command calls it first.
  - `etal validate` prints `OK: {n} notes` on success.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_validate.py
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
    j.write_text(j.read_text().replace("---\n# Genome", "issn: 0305-1048\n---\n# Genome", 1))
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_validate.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the rules in `schema.validate`**

Required properties: journal `name`, `abbreviation`, `peer_reviewed`; conference `name`, `start`, `location`, `audience`; publication `title`, `format`, `status`, `date`, `authors` (non-empty), `journal`; presentation `title` (may be empty string only when `format` is `hackathon` or `workshop`), `date`, `format`, `attendance`, `event`, `presenters` (non-empty); honor `name`, `date`, `result`, `recipient`. Enumeration message format: `"must be one of: a | b | c"`. Date-in-event rule uses `date.first_day() >= event.start.first_day()` and `date.last_day() <= event.effective_end.last_day()`. Duplicate keys: `doi`, `pmid`, `scholar_id` across publications; `issn` and `eissn` across journals; report on every note sharing the value. Alias ambiguity: for each name in `authors`, `co_first`, `corresponding`, `senior`, `coauthors`, and plain-string presenters, `len(index.candidates(name)) > 1` is a problem on that field.

- [ ] **Step 4: Add `run_validation` and the `validate` command to `cli.py`**

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/etal/schema.py src/etal/cli.py tests/test_validate.py
git commit -m "Add schema validation rules and the validate command"
```

---

### Task 7: `etal init`

**Files:**
- Create: `src/etal/init_vault.py`, `tests/test_init.py`
- Modify: `src/etal/cli.py`

**Interfaces:**
- Consumes: `config.DEFAULT_CONFIG_TEXT`, `vault.write_text`, `vault.exists`.
- Produces:
  - `init_vault.run(root: Path, dry_run: bool) -> list[Path]`: the paths it created (or would create). Creates `etal.yaml`, each folder in the default `folders` map that is a directory (not the history CSV), `Outputs/Publications.base`, `Outputs/Presentations.base`, `People/Alex Wagner.md`. Never overwrites.
  - `init_vault.PUBLICATIONS_BASE`, `init_vault.PRESENTATIONS_BASE`, `init_vault.ALEX_NOTE`: file contents.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_init.py
from click.testing import CliRunner
from etal.cli import main
from etal.init_vault import run

def test_init_creates_and_is_idempotent(tmp_path):
    created = run(tmp_path, dry_run=False)
    names = {p.relative_to(tmp_path).as_posix() for p in created}
    assert {"etal.yaml", "Outputs/Publications", "Outputs/Presentations", "Journals", "Conferences", "Honors", "Awards", "People",
            "Outputs/Publications.base", "Outputs/Presentations.base", "People/Alex Wagner.md"} <= names
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_init.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `init_vault.py`**

Base files in Obsidian's Bases YAML, the same shape as the vault's award notes:

```yaml
filters:
  and:
    - file.inFolder("Outputs/Publications")
views:
  - type: table
    name: Publications
    order:
      - title
      - date
      - journal
      - citations
      - peer_reviewed
      - grants
    sort:
      - property: date
        direction: DESC
```

`ALEX_NOTE`: frontmatter `aliases` (`Wagner AH`, `Wagner A`, `Wagner, AH`, `Wagner, A`, `Alex Wagner`, `Alex H. Wagner`), `orcid: 0000-0002-2502-8961`, `scholar_id: cwG4QRAAAAAJ`, `lab_member: true`, body `# Alex Wagner`. `init` is the one command that does not call `run_validation`; `--vault` for it means the directory to initialize and need not hold `etal.yaml` yet.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/etal/init_vault.py src/etal/cli.py tests/test_init.py
git commit -m "Add etal init"
```

---

### Task 8: Rendering helpers and the citation line

**Files:**
- Create: `src/etal/render.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: `schema.Publication`, `schema.Presentation`.
- Produces:
  - `render.markdown_table(headers: list[str], rows: list[list[str]]) -> str` (pipe table with a header separator row, cells escaped for `|`).
  - `render.csv_text(headers, rows) -> str` (RFC 4180 via `csv` module, `\n` line endings).
  - `render.nlm_citation(pub: Publication) -> str`.
  - `render.presentation_line(p: Presentation) -> str` (the part after `YYYY-MM-DD | `).
  - `render.format_label(fmt: str) -> str` and `render.FORMAT_LABELS`.
  - `render.date_prefix(d: PartialDate) -> str`: `str(d)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_render.py
from etal.render import markdown_table, csv_text, nlm_citation, presentation_line

def test_nlm_citation_full(data):
    pub = data.by_name["publications"]["2026 Druggable genome LLM"]
    assert nlm_citation(pub) == ("Schimmelpfennig L, Cannon M, Cody Q, McMichael J, Coffman AC, Kiwala S, Krysiak K, Wagner AH, Griffith M, Griffith OL. "
        "Searching the druggable genome using large language models. Bioinformatics. 2026;42(9):btag632. "
        "https://doi.org/10.1093/bioinformatics/btag632. PMID: 42631692; PMCID: PMC13544961.")

def test_nlm_citation_minimal(data):
    pub = data.by_name["publications"]["2026 Cat-VRS preprint"]
    assert nlm_citation(pub) == "Puthawala D, Reardon B, Wagner AH. " + pub.title + ". bioRxiv. 2026."

def test_presentation_line_with_people_and_override(data):
    p = data.by_name["presentations"]["2026-08-05 FUSOR poster"]
    assert presentation_line(p) == "Poster, in person | Daniel Puthawala. Standardizing fusion calls in a computable format with FUSOR. CGC Annual Meeting 2026, Satellite venue, Houston, TX. National."

def test_presentation_line_month_only_and_plain_presenter(data):
    p = data.by_name["presentations"]["2026-07 AnyVar research in review"]
    assert presentation_line(p) == "Lightning talk, virtual | Jennifer Bowser. AnyVar and AnyVLM. IGM Research in Review, Virtual. Institutional. Day not recorded."

def test_tables():
    assert markdown_table(["a", "b"], [["1", "x|y"]]) == "| a | b |\n| --- | --- |\n| 1 | x\\|y |\n"
    assert csv_text(["a", "b"], [["1", 'x,"y']]) == 'a,b\n1,"x,""y"\n'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `render.py`**

`nlm_citation` assembles: authors joined `", "`, then `. {title}.`, then ` {journal.abbreviation}.`, then ` {year}` followed by `;{volume}` if volume, `({issue})` if issue and volume, `:{pages}` if pages and volume, else `;{pages}` if pages without volume, then `.`; then ` https://doi.org/{doi}.` if doi; then ` PMID: {pmid}` and `; PMCID: {pmcid}` joined, ending `.`, if either. `year` is `pub.date.year`.

`presentation_line`: `{format_label}, {attendance} | {presenters}. {title}. {event.name}, {location}. {Audience}.` with `title` omitted (and its period) when empty, presenters as person note names or plain strings joined `", "`, audience capitalized, and ` Day not recorded.` appended when `not p.date.day_recorded`. `FORMAT_LABELS`: poster `Poster`, invited talk `Invited talk`, platform `Podium presentation`, lightning talk `Lightning talk`, workshop `Workshop session`, panel `Panel discussion`, course lecture `Course lecture`, hackathon `Hackathon`, consortium update `Consortium update`, other `Presentation`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_render.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/etal/render.py tests/test_render.py
git commit -m "Add table rendering and NLM citation line"
```

---

### Task 9: Citation report

**Files:**
- Create: `src/etal/reports/__init__.py`, `src/etal/reports/citations.py`, `tests/test_report_citations.py`, `tests/golden/citations.md`, `tests/golden/citations.csv`
- Modify: `src/etal/cli.py`

**Interfaces:**
- Consumes: `schema.VaultData`, `config.Config.stage_for`, `people.AliasIndex`, `people.author_flags`, `render.*`.
- Produces:
  - `citations.Row(title, date: str, journal: str, citations: int | None, first: bool, senior: bool, peer_reviewed: bool, first_or_corresponding_pr: bool)`
  - `citations.Totals(count: int, citations: int, first: int, senior: int)`
  - `citations.StageSection(name: str, rows: list[Row], totals: Totals)`
  - `citations.CitationReport(stages: list[StageSection], grand: Totals, fcpr_count: int, fcpr_citations: int, oldest_as_of: datetime.date | None)`
  - `citations.build(data: VaultData, person_name: str | None = None, formats: set[str] | None = None, statuses: set[str] | None = None) -> CitationReport`. Defaults: `person_name` = config `self_name`; `formats` = all except `abstract`; `statuses` = `{"published", "accepted"}`. Only publications where `is_author` is true. Stage = `pub.stage or config.stage_for(pub.date)`. With `merge_superseded`, a superseded preprint's citations are added to its successor's and the preprint is dropped.
  - `citations.render_markdown(report) -> str`, `citations.render_csv(report) -> str`.
  - CLI: `etal report citations [--output md|csv] [--format a,b] [--status a,b] [--person NAME] [--as-of] [--to PATH]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_report_citations.py
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
    data.config.merge_superseded = True
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_citations.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `reports/citations.py` and the CLI command**

Markdown layout: `# Citation report for {person}` then, per stage, `## {stage}`, the table with the eight sheet columns (`Yes`/`No` for the three flags, `TRUE`/`FALSE` for the last, blank citations as empty), then a line `Total: {count} papers, {citations} citations, {first} first or co-first, {senior} senior or corresponding.` After the stages: `## Grand Total` with the same sentence, then `First or Corresponding Peer Reviewed Total: {n} papers, {c} citations.` With `--as-of`, a final line `Counts as of {oldest_as_of} (oldest citations_as_of in the set).`

CSV layout, mirroring the sheet: columns `Stage,Title,Date,Journal,Citations,First / co-first,Senior / Corresponding,Peer Reviewed,First or Corresponding and Peer Reviewed`; one row per paper. After each stage, a totals row: Stage = the stage name, Title = `Total`, Date = count, Journal blank, Citations = citation sum, First = first count, Senior = senior count, the last two blank. Then a row with Title `Grand Total` and Stage blank in the same shape, and a row with Title `First or Corresponding Peer Reviewed Total`, Date = count, Citations = citation sum, the rest blank.

- [ ] **Step 4: Generate the golden files once, read them against the rules above, and commit them**

Run: `uv run etal --vault tests/fixtures/vault report citations --output md > tests/golden/citations.md` (after temporarily removing the two planted-problem notes, or by running against a copy). Check by eye: three stage sections, SAT1 under Predoctoral, totals equal the test's numbers. Same for CSV.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/etal/reports src/etal/cli.py tests/test_report_citations.py tests/golden
git commit -m "Add the citation report"
```

---

### Task 10: Quarter report

**Files:**
- Create: `src/etal/reports/quarter.py`, `tests/test_report_quarter.py`, `tests/golden/quarter-2026-Q3.md`
- Modify: `src/etal/cli.py`

**Interfaces:**
- Consumes: `schema.VaultData`, `people.*`, `render.nlm_citation`, `render.presentation_line`, `vault.exists`, `vault.write_text`, `vault.read_note`.
- Produces:
  - `quarter.Quarter(year: int, q: int)` with `Quarter.parse("2026-Q3")` (raises `ValueError` otherwise), `start: datetime.date`, `end: datetime.date`, `label -> "2026-Q3"`, `previous -> Quarter`, `month_names -> "July through September 2026"`.
  - `quarter.in_window(d: PartialDate, start, end) -> bool`: true when `[d.first_day(), d.last_day()]` overlaps `[start, end]`.
  - `quarter.build(data: VaultData, q: Quarter, lookback: int = 1) -> QuarterNote` where `QuarterNote` has lists of records per section: `self_publications`, `accepted`, `lab_publications`, `self_presentations`, `lab_presentations`, `honors`, `funding: list[Award]`, `conferences: list[tuple[Conference, list[Presentation]]]`, `open_items: list[str]`, `lookback_items: list[Publication | Presentation]`.
  - `quarter.render(note: QuarterNote, q: Quarter, assembled: datetime.date) -> str`.
  - `quarter.previous_note_text(data, q) -> str | None`: the body of `Outputs/{previous label} outputs.md` if present.
  - CLI: `etal report quarter 2026-Q3 [--lookback N] [--stdout] [--dry-run]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_report_quarter.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_quarter.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `reports/quarter.py` and the CLI command**

Placement rules: a publication is in the window by `date`; `self_publications` = status published and `is_author(self)`; `accepted` = status accepted and `is_author(self)`; `lab_publications` = in window, not self, with at least one author resolving to a `lab_member`. Presentations: `self_presentations` where `self` is among `presenters`, else `lab_presentations`, sorted by date. Honors by `date`. Funding: awards whose `start` is in the window. Conferences: `attended` true and `[start, effective_end]` overlapping the window, ordered by `start`, each with the presentations whose event it is. Open items: one string per month-only date (`"{note name}: day not recorded"`), per presentation with a plain-string presenter (`"{note name}: presenter '{name}' has no People note"`), per honor with no date. Lookback: items whose date falls in the `lookback` months before `q.start` and whose `title` (or `name`) does not occur in the previous quarter's note text; if that note is missing, all of them.

Rendered layout, in this order and wording:

```
---
type: outputs
quarter: 2026-Q3
kudos_due:
kudos_submitted:
---
# 2026-Q3 outputs

Publications, presentations, and funding for July through September 2026, checked back to June. Drafted by etal on 2026-10-07.

One note per quarter. Each line is written so it can be pasted into the form. Papers are placed by first online date, not issue date. Talks are placed by the date on the title slide.

## Publications

- 2026-08-22 | <nlm citation>

Accepted, not yet published:

- 2026-09-28 | <nlm citation>

Lab, without Alex as an author:

(none)

## Checked back to June

(none)

## Presentations

Alex:

- 2026-08-03 | <presentation_line>

Lab:

- 2026-07 | <presentation_line>
...

## Honors

- 2026-09 | Daniel Puthawala. GA4GH travel award, GA4GH. International. Won. Day not recorded.

## Funding

(none)

## Conferences attended

- ISMB 2026, Washington, DC, 2026-07-12 to 2026-07-16. Podium presentation.
- CGC Annual Meeting 2026, Houston, TX, 2026-08-01 to 2026-08-05. Invited talk, poster.

## Open

- 2026-07 AnyVar research in review: day not recorded
- 2026-07 AnyVar research in review: presenter 'Jennifer Bowser' has no People note
- 2026-09 GA4GH travel award: day not recorded

## Sources

- Vault notes under Outputs/Publications, Outputs/Presentations, Honors, Awards, and Conferences, as of 2026-10-07.
```

Every section prints `(none)` when empty. The "Checked back to" heading names the lookback month(s): one month gives `June`, two give `May and June`. Honor line: `{date} | {recipient name}. {name}, {venue}. {Audience}. {Result capitalized}.` plus ` Day not recorded.` when applicable. Conference line lists the distinct format labels of its presentations, lowercased after the first, joined `, `. "Today" comes from `ETAL_TODAY` (ISO) when set, else `datetime.date.today()`; put this in `cli.py` as `today()` so sync (Task 11) reuses it.

Writing: with `--stdout`, print only. Otherwise, if the target exists, print `Outputs/2026-Q3 outputs.md already exists; printing instead.` then the note; else write it (unless `--dry-run`, which prints `Would write Outputs/2026-Q3 outputs.md` and the note).

- [ ] **Step 4: Generate the golden file once, read it against the layout above, and commit it**

Run with `ETAL_TODAY=2026-10-07` against a copy of the fixture with the two planted-problem notes removed.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/etal/reports/quarter.py src/etal/cli.py tests/test_report_quarter.py tests/golden/quarter-2026-Q3.md
git commit -m "Add the quarterly outputs note report"
```

---

### Task 11: Google Scholar sync

**Files:**
- Create: `src/etal/sync/__init__.py`, `src/etal/sync/scholar.py`, `tests/fixtures/scholar/profile.json`, `tests/test_sync_scholar.py`
- Modify: `src/etal/cli.py`

**Interfaces:**
- Consumes: `schema.VaultData`, `vault.write_frontmatter`, `vault.append_csv_rows`, `vault.read_csv_rows`, `cli.today()`.
- Produces:
  - `scholar.ScholarWork(scholar_id: str, title: str, year: int | None, citations: int)`
  - `scholar.normalize_title(s: str) -> str`: NFKD then drop combining marks, casefold, replace every non-alphanumeric run with one space, strip.
  - `scholar.fetch(profile_id: str) -> list[ScholarWork]`: `scholarly.search_author_id`, then `scholarly.fill(author, sections=["publications"])`, mapping each entry's `author_pub_id`, `bib["title"]`, `bib.get("pub_year")`, `num_citations` (missing gives 0). Any exception is re-raised as `scholar.FetchError(str(exc))`.
  - `scholar.works_from_json(path: Path) -> list[ScholarWork]` for the fixture (a JSON list of objects with the four fields; a `year` may be `null`).
  - `scholar.MatchResult(matched: list[tuple[Publication, ScholarWork]], unmatched_works: list[ScholarWork], unmatched_pubs: list[Publication])`
  - `scholar.match(works, publications) -> MatchResult`: by `scholar_id` first, then by `normalize_title` equality; a work can match at most one publication and vice versa.
  - `scholar.Change(pub: Publication, old: int | None, new: int, scholar_id_added: bool)`
  - `scholar.plan(result: MatchResult, as_of: datetime.date) -> list[Change]`: one per matched pair whose `citations` differs or whose `scholar_id` is missing (unchanged counts still get a history row but no `Change`).
  - `scholar.apply(data, result, as_of, dry_run) -> list[Change]`: writes `citations`, `citations_as_of`, `scholar_id` if missing, appends `"Google Scholar, {as_of}"` to `sources` unless the last entry already starts with `Google Scholar`; appends one history row per matched pair (`as_of, note name, scholar_id, citations`). With `dry_run`, touches nothing.
  - `scholar.last_sync_date(history_path) -> datetime.date | None`.
  - CLI: `etal sync scholar [--only NOTE] [--force] [--dry-run]`. Refuses with exit 2 and `already synced today; use --force` when `last_sync_date == today()` and not `--force`. Network errors print the message and exit 2 with nothing written. `ETAL_SCHOLAR_FIXTURE=<path>` makes the command read works from that JSON instead of the network (tests use it; it also lets Alex replay a saved profile).

- [ ] **Step 1: Create `tests/fixtures/scholar/profile.json`**

Eight works: DGIdb 5.0 (id `cwG4QRAAAAAJ:dgidb5`, title with a different dash, `DGIdb 5.0: rebuilding the drug–gene interaction database for precision medicine and drug discovery platforms`, year 2024, citations 470); MAVE mapping (title exact, 2025, 12); Exon-level (title with trailing period, 2013, 131); Cat-VRS preprint (id `cwG4QRAAAAAJ:catvrs1`, title `anything`, 2026, 4) so it matches by id although the title differs; Druggable genome (exact, 2026, 1); SAT1 (exact, 2016, 11); an unmatched work `A paper not in the vault` (2019, 50) with `year: null` on one more unmatched work `Another stray` (citations 2); and Cat-VRS accepted is deliberately absent.

- [ ] **Step 2: Write the failing tests**

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_sync_scholar.py -v`
Expected: FAIL

- [ ] **Step 4: Implement `sync/scholar.py` and the CLI command**

Output: a `rich` table (`Note`, `Old`, `New`, `Scholar id`) of changes, a line `{n} updated, {m} unchanged`, then `Scholar works with no note:` and `Notes with no Scholar match:` lists (each `(none)` when empty). Import `scholarly` lazily inside `fetch` so tests and `--help` never import it.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/etal/sync tests/fixtures/scholar tests/test_sync_scholar.py src/etal/cli.py
git commit -m "Add Google Scholar citation sync"
```

---

### Task 12: End-to-end check against the migration procedure

**Files:**
- Modify: `README.md`, `docs/wheatley-migration.md` (only if a command's real flags differ from what it names)

- [ ] **Step 1: Run the full suite and the CLI help**

Run: `uv run pytest -v && uv run etal --help && uv run etal report --help && uv run etal sync --help`
Expected: all tests pass; help lists `init`, `validate`, `sync scholar`, `report citations`, `report quarter`.

- [ ] **Step 2: Walk the migration doc's A7 checks against the fixture vault**

Run, against a copy of the fixture with the two planted-problem notes removed: `etal init` (expect `[]` created except nothing new), `etal validate` (expect `OK`), `etal sync scholar` with `ETAL_SCHOLAR_FIXTURE`, `etal report citations --output csv`, `etal report quarter 2026-Q3 --stdout`. Confirm every flag the migration doc names exists; fix the doc, not the tool, where they differ.

- [ ] **Step 3: Update README usage** to the final flags, and add the `ETAL_TODAY` and `ETAL_SCHOLAR_FIXTURE` variables under a "Testing and replay" heading.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/wheatley-migration.md
git commit -m "Finish foundation: README usage and migration doc flags"
```
