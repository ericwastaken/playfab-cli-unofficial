import click

from ...pfcommand import READ_ONLY, pf_command
from .common import SESSION_NOTES, custom_id_option, emit_checked, for_each_session


@pf_command("get-user-data", READ_ONLY, ("Client/GetUserData",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@click.option("--playfab-id", "-p", "playfab_ids", multiple=True,
              help="Player to read (repeatable). Default: the logged-in player.")
@click.option("--key", "-k", "keys", multiple=True, help="UserData key (repeatable). Default: all keys.")
@click.pass_context
def get_user_data(ctx, aliases, custom_ids, playfab_ids, keys):
    """Read player UserData as a logged-in player.

    Without --playfab-id, reads the player's own data; with it, other players' data
    (PlayFab returns only what that data's permission allows). Values are strings; parse
    JSON values in a format with from_json(...).
    """

    def action(client, s):
        envs, good = [], True
        for body in [{"PlayFabId": p, **({"Keys": list(keys)} if keys else {})} for p in (playfab_ids or [s["playFabId"]])]:
            env = client.call("Client/GetUserData", body, s["sessionTicket"])
            env["customId"] = s["customId"]
            envs.append(env)
            good &= emit_checked(ctx, env, f"{client.alias} {s['customId']}")
        return good, envs

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
