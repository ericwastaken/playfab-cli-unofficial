import json
import logging
import time
from pathlib import Path

import click

from ..client import PlayFabError, TitleClient
from ..config import ConfigError
from ..pfcommand import READ_ONLY, pf_command

logger = logging.getLogger("pfcli")

PAGE = 100  # PlayFab's maximum MaxResultsCount for GetLeaderboard


def pull_board(server: TitleClient, statistic: str, want: int, pause: float):
    rows, version, start = [], None, 0
    while start < want:
        data = server.call("Server/GetLeaderboard", {
            "StatisticName": statistic,
            "StartPosition": start,
            "MaxResultsCount": PAGE,
            "ProfileConstraints": {"ShowDisplayName": True},
        })
        board = data.get("Leaderboard", [])
        version = data.get("Version", version)
        for e in board:
            name = e.get("DisplayName") or (e.get("Profile") or {}).get("DisplayName")
            rows.append({"rank": e.get("Position", 0) + 1, "name": name})
        logger.debug("%s %s: %d rows so far", server.alias, statistic, len(rows))
        if len(board) < PAGE:
            break  # end of the board
        start += PAGE
        time.sleep(pause)
    return rows[:want], version


def parse_depths(values):
    depths = {}
    for v in values:
        board, _, n = v.partition("=")
        if not n.isdigit():
            raise click.BadParameter(f"expected BOARD=N, got '{v}'", param_hint="--depth")
        depths[board] = int(n)
    return depths


@pf_command("leaderboard-names", READ_ONLY, ("Server/GetLeaderboard",))
@click.argument("aliases", nargs=-1, required=True)
@click.option("--board", "only_boards", multiple=True, help="Board label(s) from the config to pull. Default: all.")
@click.option("--depth", "depth_overrides", multiple=True, metavar="BOARD=N",
              help="Override how many ranks to pull for a board, e.g. --depth alltime=500.")
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), default=None,
              help="Output folder. Default: output/<YYMMDD>/ in this tool's folder.")
@click.option("--pause", default=0.2, show_default=True, help="Seconds between pages.")
@click.pass_context
def leaderboard_names(ctx, aliases, only_boards, depth_overrides, out, pause):
    """Pull display names from legacy leaderboards.

    ALIASES are title aliases from the --config file. Each configured board (statistic +
    depth) is pulled with Server/GetLeaderboard, current version, and written to
    <out>/<ALIAS>-<board>.json with alias, title, board, statistic, version,
    pulled_utc and rows [{rank, name}].
    """
    cfg = ctx.obj["config"]
    depths = parse_depths(depth_overrides)
    out = out or ctx.obj["root"] / "output" / time.strftime("%y%m%d")
    out.mkdir(parents=True, exist_ok=True)
    summary, failed = [], False
    for alias in aliases:
        try:
            title = cfg.title(alias)
            server = TitleClient(title)
        except (ConfigError, PlayFabError) as e:
            click.echo(f"{alias}: {e}; skipped", err=True)
            failed = True
            continue
        for board, spec in title["boards"].items():
            if only_boards and board not in only_boards:
                continue
            statistic, want = spec["statistic"], depths.get(board, spec.get("depth", 100))
            try:
                rows, version = pull_board(server, statistic, want, pause)
            except PlayFabError as e:
                click.echo(f"{server.alias} {board}: ERROR {e}", err=True)
                failed = True
                continue
            path = out / f"{server.alias}-{board}.json"
            path.write_text(json.dumps({
                "alias": server.alias, "title": server.title_id, "board": board,
                "statistic": statistic, "version": version,
                "pulled_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rows": rows,
            }, ensure_ascii=False, indent=1))
            item = {"alias": server.alias, "board": board, "statistic": statistic, "version": version,
                    "rows": len(rows), "named": sum(1 for r in rows if r["name"]), "file": str(path)}
            summary.append(item)
            if not ctx.obj["json_output"]:
                click.echo(f"{server.alias} {board} ({statistic} v{version}): {item['rows']} rows, "
                           f"{item['named']} named -> {path}")
    if ctx.obj["json_output"]:
        click.echo(json.dumps(summary, indent=2))
    ctx.exit(1 if failed else 0)
