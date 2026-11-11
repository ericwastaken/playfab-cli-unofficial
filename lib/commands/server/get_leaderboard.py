import logging
import time

import click

from ...client import PlayFabError, TitleClient, error_text, ok
from ...config import ConfigError
from ...pfcommand import READ_ONLY, pf_command

logger = logging.getLogger("pfcli")

PAGE = 100  # PlayFab's maximum MaxResultsCount for GetLeaderboard


@pf_command("get-leaderboard", READ_ONLY, ("Server/GetLeaderboard",))
@click.argument("aliases", nargs=-1, required=True)
@click.option("--statistic", "-s", required=True, help="Statistic (legacy leaderboard) name, case-sensitive.")
@click.option("--max", "max_rows", type=click.IntRange(min=1), default=100, show_default=True,
              help="How many ranks to pull per title; pages of 100 are requested until reached.")
@click.option("--start", type=click.IntRange(min=0), default=0, show_default=True,
              help="0-based position to start from.")
@click.option("--version", "stat_version", type=click.IntRange(min=0), default=None,
              help="Statistic version to read. Default: the current version.")
@click.option("--pause", type=float, default=0.2, show_default=True, help="Seconds between pages.")
@click.pass_context
def get_leaderboard(ctx, aliases, statistic, max_rows, start, stat_version, pause):
    """Read a legacy leaderboard (statistic) for one or more titles.

    One output record per page (up to 100 entries) per title, each holding PlayFab's own
    GetLeaderboard response. Display names are requested (ShowDisplayName). Reshape the
    output with --output-format, e.g. into a names list.
    """
    cfg, emit = ctx.obj.config, ctx.obj.emitter.emit
    failed = False
    for alias in aliases:
        try:
            client = TitleClient(cfg.title(alias))
        except (ConfigError, PlayFabError) as e:
            click.echo(f"{alias}: {e}; skipped", err=True)
            failed = True
            continue
        pos, end = start, start + max_rows
        while pos < end:
            body = {"StatisticName": statistic, "StartPosition": pos,
                    "MaxResultsCount": min(PAGE, end - pos),
                    "ProfileConstraints": {"ShowDisplayName": True}}
            if stat_version is not None:
                body["Version"] = stat_version
            try:
                env = client.call("Server/GetLeaderboard", body)
            except PlayFabError as e:
                click.echo(f"{client.alias}: {e}", err=True)
                failed = True
                break
            emit(env)
            if not ok(env):
                click.echo(f"{client.alias} {statistic}: {error_text(env)}", err=True)
                failed = True
                break
            got = len(env["response"]["data"].get("Leaderboard", []))
            logger.debug("%s %s: %d entries at %d", client.alias, statistic, got, pos)
            if got == 0 and pos == start:
                logger.warning("%s: no entries for statistic '%s' (PlayFab returns an empty board "
                               "for a statistic that does not exist; names are case-sensitive)",
                               client.alias, statistic)
            if got < body["MaxResultsCount"]:
                break  # end of the board
            pos += got
            if pos < end:
                time.sleep(pause)
    ctx.exit(1 if failed else 0)
