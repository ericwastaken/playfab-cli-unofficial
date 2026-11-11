#!/usr/bin/env python3
"""pfcli - read-only PlayFab utilities.

Run through uv from this folder:  uv run pfcli.py --help
"""
import logging
from pathlib import Path

import click
from dotenv import load_dotenv

from lib.commands.leaderboard_names import leaderboard_names
from lib.commands.names_report import names_report
from lib.commands.titles import titles
from lib.config import Config, ConfigError

ROOT = Path(__file__).resolve().parent


@click.group()
@click.option("--config", "config_file", type=click.Path(dir_okay=False, path_type=Path),
              default=ROOT / "pfcli.yml", show_default="pfcli.yml", help="Titles and settings (YAML).")
@click.option("--env", "env_file", type=click.Path(dir_okay=False, path_type=Path), default=ROOT / ".env",
              show_default=".env", help="Env file holding the secret keys named in the config.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              default="INFO", show_default=True, help="Logging verbosity (stderr).")
@click.option("--json", "json_output", is_flag=True, help="Print results as JSON on stdout.")
@click.pass_context
def cli(ctx, config_file, env_file, log_level, json_output):
    """pfcli - READ-ONLY PlayFab utilities, configured by a YAML config + env file."""
    logging.basicConfig(level=getattr(logging, log_level.upper()), format="%(levelname)s %(message)s")
    try:
        config = Config(config_file)
    except ConfigError as e:
        raise click.ClickException(str(e))
    if env_file.exists():
        load_dotenv(env_file, override=True)
    elif env_file != ROOT / ".env":
        raise click.ClickException(f"Missing {env_file}. Copy .env.example and fill in the keys.")
    ctx.ensure_object(dict)
    ctx.obj.update({"json_output": json_output, "root": ROOT, "config": config})


cli.add_command(titles)
cli.add_command(leaderboard_names)
cli.add_command(names_report)

if __name__ == "__main__":
    cli()
