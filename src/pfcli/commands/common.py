"""Helpers shared by commands."""
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import click

from ..client import error_text, ok

logger = logging.getLogger("pfcli")

PAGE = 100  # PlayFab's maximum MaxResultsCount for GetLeaderboard


def leaderboard_options(f):
    """--statistic/--max/--start/--version/--pause, shared by server and client get-leaderboard."""
    for opt in reversed([
        click.option("--statistic", "-s", required=True, help="Statistic (legacy leaderboard) name, case-sensitive."),
        click.option("--max", "max_rows", type=click.IntRange(min=1), default=100, show_default=True,
                     help="How many ranks to pull per title; pages of 100 are requested until reached."),
        click.option("--start", type=click.IntRange(min=0), default=0, show_default=True,
                     help="0-based position to start from."),
        click.option("--version", "stat_version", type=click.IntRange(min=0), default=None,
                     help="Statistic version to read. Default: the current version."),
        click.option("--pause", type=float, default=0.2, show_default=True, help="Seconds between pages."),
    ]):
        f = opt(f)
    return f


def page_leaderboard(call, label: str, emit, statistic: str, max_rows: int, start: int,
                     stat_version, pause: float) -> tuple[bool, dict | None]:
    """Page a leaderboard with call(body) -> envelope, emitting each page.
    Returns (success, last envelope)."""
    pos, end, env = start, start + max_rows, None
    while pos < end:
        body = {"StatisticName": statistic, "StartPosition": pos,
                "MaxResultsCount": min(PAGE, end - pos),
                "ProfileConstraints": {"ShowDisplayName": True}}
        if stat_version is not None:
            body["Version"] = stat_version
        env = call(body)
        emit(env)
        if not ok(env):
            click.echo(f"{label} {statistic}: {error_text(env)}", err=True)
            return False, env
        got = len(env["response"]["data"].get("Leaderboard", []))
        if got == 0 and pos == start:
            logger.warning("%s: no entries for statistic '%s' (PlayFab returns an empty board "
                           "for a statistic that does not exist; names are case-sensitive)", label, statistic)
        if got < body["MaxResultsCount"]:
            break
        pos += got
        if pos < end:
            time.sleep(pause)
    return True, env


def run_concurrent(fn, items, concurrency: int):
    """fn over items with up to `concurrency` threads; results come back in input order."""
    if concurrency <= 1 or len(items) <= 1:
        for it in items:
            yield fn(it)
        return
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        yield from pool.map(fn, items)
