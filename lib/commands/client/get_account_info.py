import click

from ...pfcommand import READ_ONLY, pf_command
from .common import SESSION_NOTES, custom_id_option, emit_checked, for_each_session


@pf_command("get-account-info", READ_ONLY, ("Client/GetAccountInfo",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@click.option("--playfab-id", "-p", "playfab_ids", multiple=True,
              help="Player to read (repeatable). Default: the logged-in player.")
@click.pass_context
def get_account_info(ctx, aliases, custom_ids, playfab_ids):
    """Read account info (linked accounts, created date, ...) as a logged-in player.

    Without --playfab-id, the player's own account; with it, other players'.
    """

    def action(client, s):
        envs, good = [], True
        for body in [({"PlayFabId": p} if p else {}) for p in (playfab_ids or [None])]:
            env = client.call("Client/GetAccountInfo", body, s["sessionTicket"])
            env["customId"] = s["customId"]
            envs.append(env)
            good &= emit_checked(ctx, env, f"{client.alias} {s['customId']}")
        return good, envs

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
