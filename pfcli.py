#!/usr/bin/env python3
"""pfcli - PlayFab command-line utilities.

Run through uv from this folder:  uv run pfcli.py --help
"""
import logging
import os
import sys
from functools import cached_property
from pathlib import Path

import click

from lib.commands.client.create_player import create_player
from lib.commands.client.execute_cloud_script import execute_cloud_script
from lib.commands.client.get_player_state import get_player_state
from lib.commands.client.update_player import update_player
from lib.commands.client.get_account_info import get_account_info as client_get_account_info
from lib.commands.client.get_leaderboard import get_leaderboard as client_get_leaderboard
from lib.commands.client.get_player_combined_info import get_player_combined_info as client_get_player_combined_info
from lib.commands.client.get_player_profile import get_player_profile as client_get_player_profile
from lib.commands.client.get_user_data import get_user_data as client_get_user_data
from lib.commands.client.login_with_custom_id import login_with_custom_id
from lib.commands.client.sessions import flush_sessions, list_sessions, sessions
from lib.commands.client.update_user_title_display_name import update_user_title_display_name
from lib.commands.server.get_leaderboard import get_leaderboard
from lib.commands.server.get_player_combined_info import get_player_combined_info
from lib.commands.server.get_title_data import get_title_data
from lib.commands.titles import titles
from lib.config import Config, ConfigError, Secrets, paired_secrets_path
from lib.output import Emitter, FormatError, OutputFormat, find_format
from lib.sessions import SessionStore, paired_sessions_path

ROOT = Path(__file__).resolve().parent


class App:
    """ctx.obj for every command. The config loads on first use, so --help always works."""

    def __init__(self, config_file: Path, secrets_file: Path | None, sessions_file: Path | None,
                 emitter: Emitter):
        self.root, self.config_file, self.secrets_file, self.emitter = ROOT, config_file, secrets_file, emitter
        self.sessions_file = sessions_file

    @cached_property
    def sessions(self) -> SessionStore:
        return SessionStore(self.sessions_file or paired_sessions_path(self.config_file))

    @cached_property
    def config(self) -> Config:
        secrets_file = self.secrets_file
        if secrets_file is None:
            paired = paired_secrets_path(self.config_file)
            secrets_file = paired if paired and paired.exists() else None
        try:
            return Config(self.config_file, Secrets(secrets_file))
        except ConfigError as e:
            raise click.ClickException(str(e))


@click.group()
@click.option("--config", "config_file", type=click.Path(dir_okay=False, path_type=Path),
              default=ROOT / "pfcli-config.yml", show_default="pfcli-config.yml",
              help="Titles and settings (YAML).")
@click.option("--secrets", "secrets_file", type=click.Path(dir_okay=False, path_type=Path), default=None,
              help="Secret keys by title ID (YAML). Default: the pfcli-secrets[-<client>].yml "
                   "paired with --config, if it exists.")
@click.option("--sessions", "sessions_file", type=click.Path(dir_okay=False, path_type=Path), default=None,
              help="Saved player sessions for client commands (YAML). Default: the "
                   "pfcli-sessions[-<client>].yml paired with --config.")
@click.option("--output-format", "-o", "output_format", metavar="NAME|PATH", default=None,
              help="Reshape stdout with an output format file: a bare NAME is looked up in "
                   "output-formats/ next to the config, then in this tool's folder. "
                   "Default: one JSON line per record with PlayFab's own response.")
@click.option("--raw", is_flag=True,
              help="Print only PlayFab's response for each call, without pfcli's envelope.")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              default="INFO", show_default=True, help="Logging verbosity (stderr).")
@click.pass_context
def cli(ctx, config_file, secrets_file, sessions_file, output_format, raw, log_level):
    """pfcli - PlayFab utilities, configured by a YAML config + YAML secrets file.

    Data goes to stdout (pipe it, or redirect with >); logs and errors go to stderr.
    """
    logging.basicConfig(level=getattr(logging, log_level.upper()), format="%(levelname)s %(message)s",
                        stream=sys.stderr)
    try:
        fmt = OutputFormat(find_format(output_format, config_file.parent, ROOT)) if output_format else None
    except FormatError as e:
        raise click.ClickException(str(e))
    emitter = Emitter(fmt, raw=raw)
    ctx.call_on_close(emitter.finish)
    ctx.obj = App(config_file, secrets_file, sessions_file, emitter)


@cli.group()
def server():
    """Commands that call PlayFab's Server API (title secret key)."""


@cli.group()
def client():
    """Commands that call PlayFab's Client API as a logged-in player.

    \b
    Two steps: log in once with `client login-with-custom-id` (saves the
    player's session), then run any client command with the same --custom-id.
    `client create-player | update-player | get-player-state` run the title's
    player sequences from the config. `client sessions list | flush` shows or
    removes saved sessions.
    """


cli.add_command(titles)
for cmd in (get_leaderboard, get_title_data, get_player_combined_info):
    server.add_command(cmd)
for cmd in (login_with_custom_id, client_get_leaderboard, client_get_player_profile, client_get_user_data,
            client_get_account_info, client_get_player_combined_info, update_user_title_display_name,
            execute_cloud_script, create_player, update_player, get_player_state, sessions):
    client.add_command(cmd)
sessions.add_command(list_sessions)
sessions.add_command(flush_sessions)

if __name__ == "__main__":
    try:
        cli()
    except BrokenPipeError:  # e.g. piped into head
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
