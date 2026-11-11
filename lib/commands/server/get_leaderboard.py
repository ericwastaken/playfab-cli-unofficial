import click

from ...client import PlayFabError, TitleClient
from ...config import ConfigError
from ...pfcommand import READ_ONLY, pf_command
from ..common import leaderboard_options, page_leaderboard


@pf_command("get-leaderboard", READ_ONLY, ("Server/GetLeaderboard",))
@click.argument("aliases", nargs=-1, required=True)
@leaderboard_options
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
            good, _ = page_leaderboard(lambda b: client.call("Server/GetLeaderboard", b), client.alias, emit,
                                       statistic, max_rows, start, stat_version, pause)
            failed |= not good
        except (ConfigError, PlayFabError) as e:
            click.echo(f"{alias}: {e}; skipped", err=True)
            failed = True
    ctx.exit(1 if failed else 0)
