# et-al

`et-al` tracks Alex Wagner's scholarly outputs (publications, presentations, honors) and produces the reports he now assembles by hand. It is a command line tool, `etal`, over notes in an Obsidian vault kept in git: no server, no database.

## Install

```bash
uv tool install .
```

For development, run `uv sync` and then `uv run etal --help` and `uv run pytest`.

## Vault location

Every command takes `--vault PATH`. If it is omitted, the `ETAL_VAULT` environment variable is used.

```bash
export ETAL_VAULT=~/Obsidian/Wheatley
```

## Commands

- `etal init`: create `etal.yaml`, any missing configured folders, the two `.base` files, and `People/Alex Wagner.md`; never overwrites.
- `etal validate`: parse every note in the configured folders and report problems as `path: field: message`.
- `etal sync scholar`: fetch the Google Scholar profile and update citation counts on matching publication notes.
- `etal report citations`: reproduce the Paper Citations sheet, grouped by career stage, with totals.
- `etal report quarter 2026-Q3`: draft the quarterly outputs note for the given quarter.

The tool never runs git. Commits are made by the person or agent running it.

## Documents

- [Foundation design spec](docs/superpowers/specs/2026-10-30-et-al-foundation-design.md)
- [Wheatley migration procedure](docs/wheatley-migration.md)
