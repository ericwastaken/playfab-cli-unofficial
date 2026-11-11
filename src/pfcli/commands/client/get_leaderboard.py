import click

from ...pfcommand import READ_ONLY, pf_command
from ..common import leaderboard_options, page_leaderboard
from .common import SESSION_NOTES, custom_id_option, for_each_session


@pf_command("get-leaderboard", READ_ONLY, ("Client/GetLeaderboard",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@leaderboard_options
@click.pass_context
def get_leaderboard(ctx, aliases, custom_ids, statistic, max_rows, start, stat_version, pause):
    """Read a legacy leaderboard as a logged-in player sees it.

    Same paging and output as server get-leaderboard, but through the Client API with the
    player's session, so it shows exactly what a game client can read.
    """
    emit = ctx.obj.emitter.emit

    def action(client, s):
        envs = []

        def call(body):
            env = client.call("Client/GetLeaderboard", body, s["sessionTicket"])
            env["customId"] = s["customId"]
            envs.append(env)
            return env
        good, _ = page_leaderboard(call, f"{client.alias} {s['customId']}", emit,
                                   statistic, max_rows, start, stat_version, pause)
        return good, envs

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
