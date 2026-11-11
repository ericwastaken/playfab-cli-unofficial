#!/usr/bin/env python3
"""pfcli - read-only PlayFab utilities.

Run through uv from this folder:  uv run pfcli.py --help
"""
import logging
from pathlib import Path

import click

from lib.commands.leaderboard_names import leaderboard_names
from lib.commands.names_report import names_report
from lib.commands.titles import titles
from lib.config import Config, ConfigError, Secrets, paired_secrets_path

ROOT = Path(__file__).resolve().parent


@click.group()
@click.option("--config", "config_file", type=click.Path(dir_okay=False, path_type=Path),
              default=ROOT / "pfcli-config.yml", show_default="pfcli-config.yml",
              help="Titles and settings (YAML).")
@click.option("--secrets", "secrets_file", type=click.Path(dir_okay=False, path_type=Path), default=None,
              help="Secret keys by title ID (YAML). Default: the pfcli-secrets[-<client>].yml "
                   "paired with --config, if it exists.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              default="INFO", show_default=True, help="Logging verbosity (stderr).")
@click.option("--json", "json_output", is_flag=True, help="Print results as JSON on stdout.")
@click.pass_context
def cli(ctx, config_file, secrets_file, log_level, json_output):
    """pfcli - READ-ONLY PlayFab utilities, configured by a YAML config + YAML secrets file."""
    logging.basicConfig(level=getattr(logging, log_level.upper()), format="%(levelname)s %(message)s")
    if secrets_file is None:
        paired = paired_secrets_path(config_file)
        secrets_file = paired if paired and paired.exists() else None
    try:
        config = Config(config_file, Secrets(secrets_file))
    except ConfigError as e:
        raise click.ClickException(str(e))
    ctx.ensure_object(dict)
    ctx.obj.update({"json_output": json_output, "root": ROOT, "config": config})


cli.add_command(titles)
cli.add_command(leaderboard_names)
cli.add_command(names_report)

if __name__ == "__main__":
    cli()
