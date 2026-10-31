import sys
from pathlib import Path

import click

from etal import __version__, schema
from etal.config import Config, ConfigError, find_vault, load_config


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
