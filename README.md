# et-al

`et-al` tracks Alex Wagner's scholarly outputs (publications, presentations, honors) and produces the reports he now assembles by hand. It is a command line tool, `etal`, over notes in an Obsidian vault kept in git: no server, no database.

## Install

```bash
uv tool install .
```

For development, run `uv sync` and then `uv run etal --help` and `uv run pytest`.

## Vault location

Put `--vault PATH` before the command, as in `etal --vault PATH validate`. If it is omitted, the `ETAL_VAULT` environment variable is used.

```bash
export ETAL_VAULT=~/Obsidian/Wheatley
```

## Commands

- `etal init [--dry-run]`: create `etal.yaml`, any missing configured folders, the two `.base` files, and `People/Alex Wagner.md`; never overwrites. Prints `Nothing to do` when everything exists.
- `etal validate`: parse every note in the configured folders and report problems as `path: field: message`. Prints `OK: N notes` when clean.
- `etal sync scholar [--only NOTE] [--force] [--dry-run]`: fetch the Google Scholar profile and update citation counts and Scholar ids on matching publication notes. It refuses to run twice in one day unless `--force` is given.
- `etal report citations [--output md|csv] [--format FORMATS] [--status STATUSES] [--person NAME] [--as-of] [--to PATH]`: reproduce the Paper Citations sheet, grouped by career stage, with totals. `--format` and `--status` filter publications; `--output` picks Markdown or CSV; `--as-of` adds the oldest citation date to the Markdown.
- `etal report quarter QUARTER [--lookback N] [--stdout] [--dry-run]`: draft the quarterly outputs note for a quarter such as `2026-Q3`. `--lookback` is the months before the quarter to check for unlisted items (default 1).

The tool never runs git. Commits are made by the person or agent running it.

## Testing and replay

Two environment variables make runs repeatable.

- `ETAL_TODAY`: an ISO date, such as `2026-10-31`. It fixes "today" for reports and for the once-a-day sync guard.
- `ETAL_SCHOLAR_FIXTURE`: a path to a JSON list of `{scholar_id, title, year, citations}`. It replaces the network fetch in `etal sync scholar`. The command then prints `Reading Scholar works from fixture PATH` first, and the `sources` line it writes is `Scholar fixture FILE, DATE` rather than `Google Scholar, DATE`.

A fixture run writes the fixture's counts and Scholar ids into the notes, so never point it at the real vault. The example below copies the test fixture vault to a scratch folder and names that copy with `--vault`, which overrides any `ETAL_VAULT` you have exported:

```bash
cp -R tests/fixtures/vault /tmp/etal-replay
rm "/tmp/etal-replay/Conferences/Unframed Meeting.md" "/tmp/etal-replay/Outputs/Publications/2026 Unresolved import.md"
ETAL_SCHOLAR_FIXTURE=tests/fixtures/scholar/profile.json ETAL_TODAY=2026-10-31 etal --vault /tmp/etal-replay sync scholar
```

The two removed notes are planted validation failures in the fixture; with them present, every command stops at validation.

## Documents

- [Foundation design spec](docs/superpowers/specs/2026-10-30-et-al-foundation-design.md)
- [Wheatley migration procedure](docs/wheatley-migration.md)
