import click

from ...pfcommand import READ_ONLY, pf_command
from .common import SESSION_NOTES, custom_id_option, emit_checked, for_each_session


@pf_command("get-player-profile", READ_ONLY, ("Client/GetPlayerProfile",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@click.option("--playfab-id", "-p", "playfab_ids", multiple=True,
              help="Player to read (repeatable). Default: the logged-in player.")
@click.pass_context
def get_player_profile(ctx, aliases, custom_ids, playfab_ids):
    """Read a player profile as a logged-in player.

    With --playfab-id, reads other players' profiles: one output record per target per
    session. Useful to check what one player can learn about another.
    """

    def action(client, s):
        envs, good = [], True
        for body in [{"PlayFabId": p, "ProfileConstraints": {"ShowDisplayName": True}} for p in (playfab_ids or [s["playFabId"]])]:
            env = client.call("Client/GetPlayerProfile", body, s["sessionTicket"])
            env["customId"] = s["customId"]
            envs.append(env)
            good &= emit_checked(ctx, env, f"{client.alias} {s['customId']}")
        return good, envs

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
