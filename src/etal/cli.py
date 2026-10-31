import click

from etal import __version__


@click.group()
@click.version_option(__version__)
@click.option("--vault", type=click.Path(), envvar="ETAL_VAULT", default=None)
@click.pass_context
def main(ctx, vault):
    ctx.obj = {"vault": vault}
