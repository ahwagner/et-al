# et-al foundation design

Date: 2026-10-30, revised 2026-10-31
Status: approved design with revisions from Alex's review, awaiting implementation plan
Scope: sub-project 1 of 4 (see "Roadmap" at the end)

## Purpose

`et-al` tracks Alex Wagner's scholarly outputs (publications, presentations, honors) and produces the reports he now assembles by hand:

1. **Citation report**: the "Paper Citations" Google Sheet. Papers grouped by career stage, each with its Google Scholar citation count and authorship flags, with the same totals.
2. **Quarterly outputs note**: the IGM Quarterly Kudos submission, now written by hand as `Outputs/YYYY-Qn outputs.md` in the vault.
3. **NIH RPPR product lists** per award and reporting period (sub-project 3).
4. **Profile cross-links** to ORCID, myNCBI, Zenodo, Google Scholar, PubMed (sub-project 4).

Decisions already made with Alex:

- Reports needed: promotion and CV metrics, NIH RPPR, public profile sync. Lab-wide productivity dashboards are not a goal, but the records must support lab members as presenters, recipients, and authors because RPPR and the kudos note need them.
- Form factor: a command line tool over files in git. No server, no database.
- Canonical source: Alex's Obsidian vault (private repo `ahwagner/wheatley-vault`). The tool reads and writes vault notes. His assistant, Wheatley, reformats existing notes and migrates the sheets to match this spec.
- Canonical citation source: Google Scholar. Other sources are used for identifiers and metadata, not counts.
- Journals and conferences are first-class notes that publications and presentations link to, not strings.
- The tool has no one-time commands. The migration from the sheets is a written procedure for Wheatley: `docs/wheatley-migration.md`.

## Shape

`et-al` is a Python package providing the `etal` command. It is installed on Alex's Mac and pointed at the vault. The vault is the only data store.

- **Hand-maintained facts** live in note frontmatter and are edited by Alex or Wheatley.
- **Machine-fetched facts** (citation counts, later resolved identifiers) are written into frontmatter by `etal sync`, plus one append-only history file for time series.
- **Reports** are rendered to Markdown or CSV, to stdout or to a path. The quarterly note is written into the vault.
- **Git is not the tool's job.** `etal` never runs git. Wheatley commits what the tool wrote under the vault's own rules (`System/procedures/git.md`). This keeps the vault's one-committer convention intact.
- **Obsidian is not required.** The tool parses Markdown and YAML directly. Bases view files are provided so the same records render as tables inside Obsidian, but nothing depends on them.

## Vault schema

### Conventions carried over from the vault

- Every note has YAML frontmatter with a `type` property. Folders group by type; Bases filters use `file.inFolder(...)` and `type`.
- Links between notes are wikilinks. In a property, each link is quoted: `- "[[Note name]]"`.
- `Awards/` means funding awards (grants). This spec keeps that meaning. Prizes and recognitions go in a new `Honors/` folder.
- `Conferences/` already holds one note per event Alex attends, with his notes from it. This spec makes those notes the event entity that presentations link to.
- Dates are ISO: `YYYY-MM-DD`. Where only the month is known, `YYYY-MM` is allowed and reported as "day not recorded".
- The tool never deletes or renames notes. Renames are Alex's or Wheatley's, through the Obsidian command line.

### Folder layout

```
Outputs/
  Publications/         one note per publication
  Presentations/        one note per presentation
  Publications.base     Bases table of publications (shipped by etal init)
  Presentations.base    Bases table of presentations
  citation-history.csv  append-only, written by etal sync scholar
  YYYY-Qn outputs.md    quarterly note, drafted by etal report quarter
Journals/               one note per journal or preprint server
Conferences/            existing: one note per event, gains properties
Honors/                 one note per prize, nomination, or recognition
Awards/                 existing grant notes, gain a few properties
People/                 existing person notes, gain a few properties
etal.yaml               tool configuration, vault root
```

### Entity relationships

```
Publication  --journal-->      Journal
Publication  --grants-->       Award (many)
Publication  --authors-->      printed names, resolved to People through aliases
Publication  --supersedes-->   Publication (preprint)
Presentation --event-->        Conference
Presentation --presenters-->   People (many), or plain names
Presentation --grants-->       Award (many)
Honor        --recipient-->    Person
Honor        --related-->      Publication or Presentation
```

Properties that a child can inherit from its parent are marked "defaults from" below. The child's own value, when present, wins.

### Journal note

Path: `Journals/<full name>.md`. Example: `Journals/Nucleic Acids Research.md`. Preprint servers are journal notes too, so a preprint has somewhere to point.

```yaml
---
type: journal
name: Nucleic Acids Research
abbreviation: Nucleic Acids Res     # NLM Title Abbreviation, used in citation lines
issn: 0305-1048
eissn: 1362-4962
publisher: Oxford University Press
url: https://academic.oup.com/nar
peer_reviewed: true                 # default for publications in this journal
nlm_id:                             # NLM Catalog id, for sub-project 2
---
# Nucleic Acids Research
```

Rules:

- `name` and `abbreviation` are required. `peer_reviewed` is required because publications default to it.
- Citation lines use `abbreviation`. The citation report and the quarterly note print `abbreviation`; the Bases view shows the note name.
- A preprint server note (bioRxiv, medRxiv, arXiv, OSF Preprints) sets `peer_reviewed: false`.

### Conference note

Path: `Conferences/<event name>.md`, the existing convention. Example: `Conferences/GA4GH 14th Plenary.md`. One note per event instance, so "ISMB 2024" and "ISMB 2026" are two notes with the same `series`.

```yaml
---
type: conference
name: GA4GH 14th Plenary and Connect
series: GA4GH Plenary               # the recurring meeting, for grouping; blank for a one-off
start: 2026-09-28
end: 2026-10-02
location: Singapore                 # city and region, or "Virtual"
modality: in person                 # how the meeting was held: in person | virtual | hybrid
audience: international             # international | national | regional | institutional | local
organizer: GA4GH
url:
attended: true                      # Alex attended, for the "Conferences attended" section
---
# GA4GH 14th Plenary and Connect

Alex's notes from the meeting, as today.
```

Rules:

- `name`, `start`, `location`, `audience` are required. `end` defaults to `start`. `modality` defaults to `in person` unless `location` is `Virtual`.
- The two existing conference notes have no frontmatter. Wheatley adds it during migration; until then `etal validate` lists them as missing `type`.
- A seminar series, a university visit, or a webinar gets a conference note too. The note can be nearly empty; the point is one place for the event's properties and Alex's notes.

### Publication note

Path: `Outputs/Publications/<year> <short title>.md`. The short title is a few words chosen at creation; the full title is a property. Example: `Outputs/Publications/2024 DGIdb 5.0.md`.

```yaml
---
type: publication
title: "DGIdb 5.0: rebuilding the drug-gene interaction database for precision medicine and drug discovery platforms"
kind: article            # article | preprint | review | book chapter | white paper | dataset | software | abstract | other
status: published        # published | accepted | submitted | preprint | in preparation
date: 2024-01-05         # first online date, the date reports place the paper by
journal: "[[Nucleic Acids Research]]"
volume: "52"
issue: D1
pages: D1227-D1235
authors:                 # ordered, as printed on the paper
  - Cannon M
  - Stevenson J
  - Stahl K
  - Basu R
  - Coffman A
  - Kiwala S
  - McMichael JF
  - Kuzma K
  - Morrissey D
  - Cotto K
  - Mardis ER
  - Griffith OL
  - Griffith M
  - Wagner AH
co_first: []             # printed names sharing first authorship; empty means only authors[0]
corresponding:           # printed names marked corresponding
  - Wagner AH
senior: []               # printed names counted as senior; empty means the last author
peer_reviewed:           # defaults from the journal; set only to override
doi: 10.1093/nar/gkad1040
pmid: "37953380"
pmcid: PMC10767982
url:                     # for outputs without a DOI (white papers, some preprints)
scholar_id: cwG4QRAAAAAJ:abc123     # Google Scholar "citation_for_view" id, written by sync
citations: 458           # written by etal sync scholar, or by hand
citations_as_of: 2026-10-30
grants:
  - "[[CIViC U24]]"
  - "[[R35]]"
supersedes:              # wikilink to the preprint note this published version replaces
stage:                   # career stage override, by name from etal.yaml; set when the work predates its publication date
sources:                 # where the record's values came from, one line per source, newest last
  - PubMed record, 2026-10-31
  - Paper Citations sheet, read 2026-10-31
notes:                   # short free text that reports may print
---
# DGIdb 5.0

Free text. Reviewer history, where the data lives, anything else.
```

Rules:

- `sources` is optional on every output note type (publication, presentation, honor). It is provenance for merges, written by Wheatley during imports and by `etal sync` when it changes a value. Reports ignore it.
- `title`, `kind`, `status`, `date`, `authors`, `journal` are required. `journal` must resolve to a `Journals/` note. A white paper, dataset, or software release with no venue uses a journal note for its host (Zenodo, GitHub, the publishing body) so the rule has no exceptions.
- `authors` entries are the printed form. Matching a printed name to a `People/` note goes through that note's `aliases`.
- A preprint and its published version are two notes. The published note links the preprint through `supersedes`. The citation report counts the published note and folds the preprint's citations into it only when `etal.yaml` sets `merge_superseded: true` (default false, matching how Scholar usually lists them separately).
- `pmid` and `volume` are quoted so YAML keeps them as strings.
- A publication's career stage is the stage in `career_stages` whose range contains `date`, unless `stage` names one. The override exists because the sheet files work by where it was done: the 2016 SAT1 paper is predoctoral work published a year into the postdoc. `etal validate` rejects a `stage` that names no configured stage.
- Authorship flags are derived, never stored. For a person P with aliases A:
  - first or co-first: `authors[0]` in A, or any name in `co_first` in A.
  - senior or corresponding: any name in `corresponding` in A, or (`senior` empty and `authors[-1]` in A), or any name in `senior` in A.
  - "first or corresponding peer reviewed": either flag above, and the effective `peer_reviewed` true.

### Presentation note

Path: `Outputs/Presentations/<date> <short title>.md`. Example: `Outputs/Presentations/2026-08-03 ClinVar automation CGC.md`.

```yaml
---
type: presentation
title: Automating somatic cancer submissions to ClinVar with GA4GH genomic knowledge standards
date: 2026-08-03         # YYYY-MM allowed
kind: invited talk       # poster | invited talk | platform | lightning talk | workshop | panel | course lecture | hackathon | consortium update | other
event: "[[CGC Annual Meeting 2026]]"
session:                 # optional, named session or track
location:                # defaults from the event
modality:                # how this talk was given, in person | virtual | hybrid; defaults from the event, set only for a virtual talk into an in-person meeting or the reverse
audience:                # defaults from the event
presenters:              # ordered wikilinks to People notes; co-presenters outside the lab may be plain names
  - "[[Alex Wagner]]"
coauthors: []            # printed names on the abstract who did not present, optional
grants:
  - "[[CIViC U24]]"
slides: https://docs.google.com/presentation/d/...
poster:
abstract_doi:
notes:
---
# ClinVar automation at CGC 2026

Free text.
```

Rules:

- `title`, `date`, `kind`, `event`, `presenters` are required. `event` must resolve to a `Conferences/` note. A hackathon or unconference entry may have an empty `title`; the report prints the event.
- `location`, `modality`, and `audience` are set on the presentation only when they differ from the event, for example a talk given virtually into an in-person meeting.
- A presenter entry that is a wikilink must resolve to a `People/` note. A plain string is accepted for people outside the lab and reported as is.
- Presentations are reported by `date`. A `YYYY-MM` date sorts first within its month and prints "day not recorded". `date` must fall within the event's `start` and `end` when both are set; `etal validate` reports a date outside it.

### Honor note

Path: `Honors/<date> <name>.md`. Example: `Honors/2024-12-02 BSGP Distinguished Research Mentor Award.md`.

```yaml
---
type: honor
name: BSGP Distinguished Research Mentor Award
date: 2024-12-02
result: won              # won | nominated | finalist
venue: Ohio State University
event:                   # optional wikilink to the Conferences note where it was given
audience: institutional  # international | national | regional | institutional | local; defaults from event
recipient: "[[Alex Wagner]]"
related:                 # optional wikilink to the presentation or publication it recognizes
notes:
---
# BSGP Distinguished Research Mentor Award
```

### People note additions

Existing `People/` notes keep their current properties (`things_tag`) and body. These are added when relevant:

```yaml
aliases:                 # printed forms, used to match authors and presenters
  - Kuzma K
  - Kuzma, K
  - Kori Kuzma
orcid: 0000-0002-...
scholar_id: ...
lab_member: true
tenure:
  - start: 2020-09-01
    end:                 # empty while current
    role: research software engineer
```

A note `People/Alex Wagner.md` is created; none exists today. `etal.yaml` names it as `self`.

### Awards note additions

```yaml
grant_number: U24CA305456
funder: NCI
role: MPI                # PI | contact PI | MPI | co-I | OSC | consultant
start: 2024-09-01
end: 2029-08-31
```

Existing `type`, `status`, `stage`, body, and the embedded Bases block are untouched.

### Configuration: `etal.yaml`

```yaml
self: "[[Alex Wagner]]"
scholar_profile: cwG4QRAAAAAJ
career_stages:           # reports group publications by the stage containing date, unless the note sets stage
  - name: Predoctoral
    until: 2014-12-31    # PhD, University of Iowa, completed 12/2014
  - name: Postdoctoral
    until: 2020-08-02    # postdoctoral fellow 01/2015 to 07/2019, then Instructor of Medicine, Washington University, to 08/2020
  - name: Nationwide Children's Hospital   # Principal Investigator from 2020-08-03; Associate Professor from 2026-06-04
merge_superseded: false
folders:                 # defaults shown; override only if the vault moves them
  publications: Outputs/Publications
  presentations: Outputs/Presentations
  journals: Journals
  conferences: Conferences
  honors: Honors
  awards: Awards
  people: People
  history: Outputs/citation-history.csv
```

### Citation history

`Outputs/citation-history.csv`, append-only, one row per publication per sync run:

```
as_of,note,scholar_id,citations
2026-10-30,2024 DGIdb 5.0,cwG4QRAAAAAJ:abc123,458
```

`note` is the note's basename without extension. The file is the source for any later time series or "citations gained this period" report.

### Bases views: the spreadsheet view over the notes

Bases is Obsidian's built-in database feature, enabled in this vault. A base is a saved query over notes: a filter (which notes), a set of columns (which properties), and a sort, rendered as a table. It holds no data of its own. Every cell is read live from a note's frontmatter, and editing a cell in the table writes that property back into the note. Delete the base and nothing is lost; delete a note and its row disappears.

So a base does for the vault what the Paper Citations sheet does today, with one difference: the table and the records are the same thing. A base is defined either in a standalone `.base` file, which opens as its own tab, or in a `base` code block inside a note, which the award notes in this vault already use to list the outcomes that link to them.

`etal init` writes two standalone files, as a convenience for looking at and hand-editing the records:

- `Outputs/Publications.base`: every note in `Outputs/Publications`, columns title, date, journal, citations, peer_reviewed, grants, sorted by date descending.
- `Outputs/Presentations.base`: every note in `Outputs/Presentations`, columns date, kind, event, presenters, audience, grants, sorted by date descending.

They are plain YAML in Obsidian's Bases format, and Obsidian's own editor can change them (add a column, change a sort). The tool never rewrites one that exists, and nothing in the tool reads them. Reports are computed from the notes, not from a base.

A journal or conference note can also carry an embedded base listing the publications or presentations that link to it, in the same pattern the award notes use. Wheatley adds those from a template; the tool does not.

## Command line

All commands take `--vault PATH` (default: `ETAL_VAULT` environment variable, then the current directory if it holds `etal.yaml`). Writer commands take `--dry-run` and print what they would change. Every command exits non-zero on a validation failure and names the file and field.

### `etal init`

Creates `etal.yaml` with defaults, any configured folder that is missing, the two `.base` files, and `People/Alex Wagner.md` if missing. Never overwrites. Safe to run again.

### `etal validate`

Parses every note in the configured folders. Checks:

- required properties present, enumerated values valid, dates parse;
- every wikilink in `journal`, `event`, `grants`, `presenters`, `recipient`, `supersedes`, `related` resolves to a note in the expected folder;
- a presentation's `date` falls within its event's `start` and `end` when those are set;
- no two publication notes share a DOI, PMID, or `scholar_id`; no two journal notes share an ISSN;
- every author or presenter name that matches a `lab_member` alias resolves to exactly one person (a name matching two people is an error; a name matching none is fine).

Prints one line per problem, `path: field: message`, then a count. This is also the first step of every other command, and a failure stops that command.

### `etal sync scholar`

Fetches the profile named by `scholar_profile` with the `scholarly` library. One profile load returns every work with its title, year, and citation count, so the run makes a handful of requests.

Matching, in order:

1. `scholar_id` stored in the note.
2. Normalized title equality (lowercase, punctuation and whitespace collapsed, diacritics folded).
3. Nothing else. Fuzzy matching is deliberately absent; near misses are reported for a human to resolve by adding `scholar_id`.

For each match: set `citations` and `citations_as_of`, write `scholar_id` if missing, append a history row, and append "Google Scholar, YYYY-MM-DD" to `sources` if the last entry is not already a Scholar line. Frontmatter is rewritten with the original key order and other properties untouched. The body is never modified.

Output: a table of updated notes with old and new counts, then two lists: Scholar works with no note, and notes with no Scholar match. `--only NOTE` restricts the run.

Risks and limits, stated plainly: Google Scholar has no API and blocks aggressive scraping. The tool runs the profile fetch once per invocation, refuses to run more than once per day unless `--force`, and uses no proxy pool. If Scholar refuses, the command exits non-zero, changes nothing, and `citations` can be edited by hand. Scraping Scholar is outside its terms of service; Alex accepts this for his own profile.

### `etal report citations`

Reproduces the Paper Citations sheet for `self` (or `--person "[[Name]]"`).

- Groups publications by `career_stages`, ordered by date within a stage.
- Columns: title, date, journal abbreviation, citations, first or co-first, senior or corresponding, peer reviewed, first-or-corresponding-and-peer-reviewed.
- Per-stage totals: count, citations, first count, corresponding count. Grand total, plus the "first or corresponding peer reviewed" count and citation sum.
- `--format md|csv`, `--kind article,review` (default: everything except `abstract`), `--status published` (default: published and accepted), `--as-of` prints the oldest `citations_as_of` in the set so the reader knows how fresh the counts are.

### `etal report quarter 2026-Q3`

Drafts the quarterly outputs note in the format of the existing `Outputs/2026-Q3 outputs.md`.

- Window: the quarter, with publications placed by `date` and presentations by `date`. `--lookback 1` (default) also lists items from the prior month that are missing from the previous quarter's note, under "Checked back to".
- Sections, in the existing note's order: Publications (Alex an author; then accepted not yet published; then lab without Alex), Presentations (Alex; then lab), Honors, Funding (awards whose `start` falls in the window), Conferences attended (conference notes with `attended: true` overlapping the window, with the presentations given there), Open (items with month-only dates or missing links), Sources.
- Line formats match the existing note exactly: `YYYY-MM-DD | Kind, modality | Presenters. Title. Event name, Location. Audience.` and the NLM-style citation line for publications, built from the note's properties and the journal's abbreviation.
- Writes to `Outputs/2026-Q3 outputs.md` only when that file does not exist; otherwise prints to stdout for Wheatley to merge. `--stdout` always prints.

### Deferred to later sub-projects

`etal sync ids` (Crossref, NCBI ID converter, OpenAlex, NLM Catalog; fills `doi`, `pmid`, `pmcid`, `authors`, journal `issn` and `nlm_id`, and flags papers out of NIH public access compliance), `etal report rppr`, `etal sync orcid`, and the profile diff reports are named here so the schema leaves room for them, and specified in their own documents.

## Internal structure

```
src/etal/
  cli.py            argument parsing only; each subcommand calls one function below
  config.py         load and validate etal.yaml, resolve folders
  vault.py          read a folder of notes into records; write frontmatter back preserving order and body
  schema.py         dataclasses for Publication, Presentation, Honor, Journal, Conference, Person, Award; validation rules; inheritance of defaults
  people.py         alias index; resolve printed names to people; derive authorship flags
  sync/scholar.py   fetch, match, update, history
  reports/citations.py
  reports/quarter.py
  render.py         Markdown and CSV table helpers; the NLM citation line
tests/
  fixtures/vault/   a small vault covering every type and edge case (month-only date, co-first, preprint + published pair, unmatched presenter, presentation overriding its event's modality, conference note without frontmatter)
  fixtures/scholar/ recorded profile responses
```

Dependencies: `python-frontmatter` or a thin wrapper over `PyYAML` that preserves key order (`ruamel.yaml` if round-trip fidelity proves necessary), `scholarly`, `click`, `rich` for tables. Python 3.12. Packaging with `pyproject.toml` and `uv`; tests with `pytest`.

Boundaries worth stating:

- `vault.py` is the only module that touches the file system. Everything else works on records, so reports and sync are testable against in-memory data.
- `schema.py` owns link resolution and default inheritance (publication from journal, presentation and honor from conference). Reports see effective values and never look at the parent themselves.
- `people.py` owns every name-matching rule. Nothing else compares names.
- `sync/scholar.py` separates `fetch()` (network) from `match()` and `apply()` (pure), so tests use recorded responses.

## Error handling

- Validation failures stop the command before any write. The message names the path and field and the accepted values.
- A network failure in sync leaves every note untouched and exits non-zero with the underlying error.
- A note whose frontmatter cannot be parsed as YAML is reported and skipped by `validate` and blocks writer commands.
- The history CSV is appended atomically (write to a temp file, then rename) so an interrupted run cannot truncate it.
- Writer commands print a one-line summary per changed file. With `--dry-run`, they print the same summary and change nothing.

## Testing

- Unit tests for name matching, flag derivation, default inheritance, date parsing (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`), title normalization, and the NLM citation line.
- Round-trip tests: read a fixture note, write it back with one property changed, assert the body and every other property are byte-identical.
- Sync tests against recorded Scholar responses, including an unmatched work and a title that differs only in punctuation.
- Report tests compare rendered output to golden files for the fixture vault, including the quarter note.
- No test touches the network.

## Migration

Populating the vault is Wheatley's work, done by hand under the vault's own rules, following `docs/wheatley-migration.md`. Alex has tracked outputs in several places over the years (the two Google Sheets, quarterly notes, biosketches, CVs, and others), and they do not fully agree, so that document is a general import-and-merge procedure: how to inventory a source, map it to the schema, match its records to existing notes, merge without losing anything, record provenance in `sources`, and check the result. The two sheets, the quarterly notes, and the biosketch are worked examples in it. In outline:

1. Wheatley creates the journal, conference, and missing people notes first, then publications, presentations, and honors, one source at a time in order of reliability, committing each batch under the vault's git rules.
2. Each later source is matched against what exists and merged: blanks filled, conflicts recorded and queued for Alex, never silently overwritten.
3. Once `etal` is installed: `etal init`, `etal validate`, fix what it lists, `etal sync scholar`, then `etal report citations` and compare totals and flags to the sheet. Flag differences point at `co_first`, `corresponding`, or `senior` lists to correct.
4. From then on, new outputs are added as notes, and the quarterly note starts from `etal report quarter`.

## Roadmap

1. **Foundation** (this spec): schema, `init`, `validate`, `sync scholar`, `report citations`, `report quarter`; the Wheatley migration procedure.
2. **Identifiers and compliance**: `sync ids` via Crossref, NCBI, OpenAlex, NLM Catalog; author lists and journal identifiers filled from metadata; NIH public access (PMCID) check; iCite metrics as additional properties.
3. **RPPR**: `report rppr` per award and period, in the order and wording section C.1 wants; presentations and honors included as "other products".
4. **Profile cross-links**: ORCID read and push, myNCBI bibliography diff, Zenodo and Google Scholar presence diff; a `links` property on publications listing where each record exists.
