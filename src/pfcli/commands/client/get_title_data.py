import click

from ...pfcommand import READ_ONLY, pf_command
from .common import SESSION_NOTES, custom_id_option, emit_checked, for_each_session


@pf_command("get-title-data", READ_ONLY, ("Client/GetTitleData",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@click.option("--key", "-k", "keys", multiple=True, help="TitleData key to read (repeatable). Default: all keys.")
@click.pass_context
def get_title_data(ctx, aliases, custom_ids, keys):
    """Read TitleData as a logged-in player sees it.

    Same as server get-title-data, but through the Client API with the player's session,
    so it shows which TitleData a game client can read. Keys that don't exist (or that the
    client can't read) are simply absent and reported on stderr.
    """
    body = {"Keys": list(keys)} if keys else {}

    def action(client, s):
        env = client.call("Client/GetTitleData", body, s["sessionTicket"])
        env["customId"] = s["customId"]
        good = emit_checked(ctx, env, f"{client.alias} {s['customId']}")
        if good and keys:
            missing = [k for k in keys if k not in ((env["response"].get("data") or {}).get("Data") or {})]
            if missing:
                click.echo(f"{client.alias} {s['customId']}: key(s) not returned: {', '.join(missing)}", err=True)
        return good, [env]

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
