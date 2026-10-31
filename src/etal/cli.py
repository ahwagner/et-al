import datetime as dt
import io
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from etal import __version__, init_vault, schema
from etal.config import Config, ConfigError, find_vault, load_config, parse_wikilink
from etal.reports import citations as citations_report
from etal.reports import quarter as quarter_report
from etal.sync import scholar as scholar_sync
from etal.vault import exists, write_text


def today() -> dt.date:
    """Today's date; ETAL_TODAY (ISO) overrides it so reports are reproducible."""
    override = os.environ.get("ETAL_TODAY")
    return dt.date.fromisoformat(override) if override else dt.date.today()


def run_validation(vault: Path) -> tuple[Config, schema.VaultData]:
    """Load the vault and stop with exit code 1 on any problem. Every command but init starts here."""
    try:
        config = load_config(vault)
    except ConfigError as exc:
        click.echo(str(exc))
        sys.exit(1)
    data = schema.load(config)
    problems = schema.validate(data)
    if problems:
        for problem in problems:
            click.echo(str(problem))
        click.echo("1 problem" if len(problems) == 1 else f"{len(problems)} problems")
        sys.exit(1)
    return config, data


def _vault_from(ctx: click.Context) -> Path:
    try:
        return find_vault(ctx.obj["vault"])
    except ConfigError as exc:
        click.echo(str(exc))
        sys.exit(1)


@click.group()
@click.version_option(__version__)
@click.option("--vault", type=click.Path(), envvar="ETAL_VAULT", default=None)
@click.pass_context
def main(ctx, vault):
    ctx.obj = {"vault": vault}


@main.command()
@click.pass_context
def validate(ctx):
    """Check every note against the schema."""
    _, data = run_validation(_vault_from(ctx))
    count = sum(len(records) for records in (
        data.journals, data.conferences, data.people, data.awards,
        data.publications, data.presentations, data.honors,
    ))
    click.echo(f"OK: {count} notes")


@main.command()
@click.option("--dry-run", is_flag=True, help="List what would be created without writing.")
@click.pass_context
def init(ctx, dry_run):
    """Create the config, folders, Bases views, and your People note where missing."""
    root = Path(ctx.obj["vault"] or os.environ.get("ETAL_VAULT") or ".").expanduser().resolve()
    try:
        created = init_vault.run(root, dry_run)
    except ConfigError as exc:
        raise click.ClickException(str(exc))
    if not created:
        click.echo("Nothing to do")
        return
    verb = "Would create" if dry_run else "Created"
    for path in created:
        click.echo(f"{verb} {path.relative_to(root).as_posix()}")


@main.group()
def report():
    """Render a report from the notes."""


def _csv_set(ctx, param, value):
    return None if value is None else {item.strip() for item in value.split(",") if item.strip()}


def _check_values(option: str, values: set[str] | None, allowed: list[str]) -> None:
    unknown = sorted(values - set(allowed)) if values else []
    if unknown:
        raise click.ClickException(
            f"{option}: unknown {', '.join(repr(v) for v in unknown)}; must be one of: {' | '.join(allowed)}"
        )


@report.command("citations")
@click.option("--output", "output", type=click.Choice(["md", "csv"]), default="md", show_default=True)
@click.option("--format", "formats", callback=_csv_set, default=None, help="Publication formats, comma separated.")
@click.option("--status", "statuses", callback=_csv_set, default=None, help="Publication statuses, comma separated.")
@click.option("--person", "person", default=None, help="People note name, as Name or [[Name]]. Defaults to you.")
@click.option("--as-of", "as_of", is_flag=True, help="Add the oldest citations_as_of date to the Markdown.")
@click.option("--to", "to", type=click.Path(path_type=Path), default=None, help="Write to this path instead of printing.")
@click.pass_context
def citations_cmd(ctx, output, formats, statuses, person, as_of, to):
    """Publications by career stage with citation counts and authorship flags."""
    _check_values("--format", formats, schema.PUBLICATION_FORMATS)
    _check_values("--status", statuses, schema.PUBLICATION_STATUSES)
    if person is not None:
        person = parse_wikilink(person) or person.strip()
    _, data = run_validation(_vault_from(ctx))
    try:
        result = citations_report.build(data, person, formats, statuses)
    except ValueError as exc:
        raise click.ClickException(str(exc))
    text = citations_report.render_csv(result) if output == "csv" else citations_report.render_markdown(result, as_of)
    if to is not None:
        write_text(to, text)
    else:
        click.echo(text, nl=False)


@report.command("quarter")
@click.argument("quarter_label", metavar="QUARTER")
@click.option("--lookback", type=click.IntRange(min=0), default=1, show_default=True, help="Months before the quarter to check for unlisted items.")
@click.option("--stdout", "to_stdout", is_flag=True, help="Print the note without writing it.")
@click.option("--dry-run", is_flag=True, help="Print what would be written without writing.")
@click.pass_context
def quarter_cmd(ctx, quarter_label, lookback, to_stdout, dry_run):
    """Draft the quarterly outputs note, for example 2026-Q3."""
    config, data = run_validation(_vault_from(ctx))
    try:
        q = quarter_report.Quarter.parse(quarter_label)
        note = quarter_report.build(data, q, lookback)
    except ValueError as exc:
        raise click.ClickException(str(exc))
    text = quarter_report.render(note, q, today())
    target = config.folder("publications").parent / f"{q.label} outputs.md"
    shown = target.relative_to(config.root).as_posix()
    if not to_stdout:
        if exists(target):
            click.echo(f"{shown} already exists; printing instead.")
        elif dry_run:
            click.echo(f"Would write {shown}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            write_text(target, text)
            click.echo(f"Wrote {shown}")
            return
    click.echo(text, nl=False)


@main.group()
def sync():
    """Pull data from outside the vault into the notes."""


@sync.command("scholar")
@click.option("--only", "only", default=None, metavar="NOTE", help="Sync just this publication note.")
@click.option("--force", is_flag=True, help="Sync even if a sync already ran today.")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
@click.pass_context
def scholar_cmd(ctx, only, force, dry_run):
    """Update citation counts and Scholar ids from your Google Scholar profile."""
    fixture = os.environ.get("ETAL_SCHOLAR_FIXTURE")
    if fixture:
        click.echo(f"Reading Scholar works from fixture {fixture}")
    config, data = run_validation(_vault_from(ctx))
    names = {pub.note.name for pub in data.publications}
    if only is not None and only not in names:
        raise click.ClickException(f"no publication note named {only!r}")
    as_of = today()
    if not force and scholar_sync.last_sync_date(config.history_path) == as_of:
        click.echo("already synced today; use --force")
        sys.exit(2)
    try:
        works = scholar_sync.works_from_json(Path(fixture)) if fixture else scholar_sync.fetch(config.scholar_profile)
    except scholar_sync.FetchError as exc:
        click.echo(str(exc))
        sys.exit(2)
    result = scholar_sync.match(works, data.publications)
    if only is not None:
        result = scholar_sync.only(result, only)
    source = scholar_sync.fixture_source(Path(fixture)) if fixture else scholar_sync.SCHOLAR_SOURCE
    changes = scholar_sync.apply(data, result, as_of, dry_run, source=source)

    if changes:
        table = Table()
        table.add_column("Note", no_wrap=True)
        table.add_column("Old", justify="right")
        table.add_column("New", justify="right")
        table.add_column("Scholar id", no_wrap=True)
        works_by_note = {pub.note.name: work for pub, work in result.matched}
        for change in changes:
            name = change.pub.note.name
            table.add_row(
                name,
                "" if change.old is None else str(change.old),
                str(change.new),
                works_by_note[name].scholar_id + (" (new)" if change.scholar_id_added else ""),
            )
        buffer = io.StringIO()
        Console(file=buffer, width=240, color_system=None, force_terminal=False).print(table)
        click.echo(buffer.getvalue(), nl=False)
    verb = "Would write" if dry_run else "Wrote"
    for path in scholar_sync.files_written(data, result):
        shown = path.relative_to(config.root).as_posix() if path.is_relative_to(config.root) else str(path)
        click.echo(f"{verb} {shown}")
    refreshed = len(result.matched) - len(changes)
    click.echo(f"{len(changes)} updated, {refreshed} refreshed")
    click.echo("Scholar works with no note:")
    for work in result.unmatched_works:
        click.echo(f"  {work.title} ({work.year or 'n.d.'}, {work.citations} citations)")
    if not result.unmatched_works:
        click.echo("  (none)")
    click.echo("Notes with no Scholar match:")
    for pub in result.unmatched_pubs:
        click.echo(f"  {pub.note.name}")
    if not result.unmatched_pubs:
        click.echo("  (none)")
    if dry_run:
        click.echo("Dry run: nothing written.")
