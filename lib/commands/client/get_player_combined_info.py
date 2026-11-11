import click

from ...inputs import InputError, build_bodies, load_template, parse_vars
from ...pfcommand import READ_ONLY, pf_command
from ..server.get_player_combined_info import DEFAULT_REQUEST
from .common import SESSION_NOTES, custom_id_option, emit_checked, for_each_session, session_vars, var_option


@pf_command("get-player-combined-info", READ_ONLY, ("Client/GetPlayerCombinedInfo",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@click.option("--playfab-id", "-p", "playfab_ids", multiple=True,
              help="Player to read (repeatable). Default: the logged-in player.")
@click.option("--request", "-r", "request_spec", metavar="NAME|PATH",
              help="Request template (request-templates/NAME.yml); $.PlayFabId is the target player. "
                   "Default: profile with display name.")
@var_option
@click.pass_context
def get_player_combined_info(ctx, aliases, custom_ids, playfab_ids, request_spec, var_pairs):
    """Read combined player info as a logged-in player.

    Uses the same request templates as server get-player-combined-info, so the same
    question can be asked with the secret key and as a player, and the answers compared.
    """
    app = ctx.obj
    try:
        template = load_template(request_spec, DEFAULT_REQUEST, app.config.path.parent, app.root)
        variables = parse_vars(var_pairs)
    except InputError as e:
        raise click.ClickException(str(e))

    def action(client, s):
        targets = list(playfab_ids) or [s["playFabId"]]
        try:
            bodies = build_bodies(template, [{"PlayFabId": t} for t in targets],
                                  {**variables, **session_vars(s, client.title_id)})
        except InputError as e:
            raise click.ClickException(str(e))
        envs, good = [], True
        for body in bodies:
            env = client.call("Client/GetPlayerCombinedInfo", body, s["sessionTicket"])
            env["customId"] = s["customId"]
            envs.append(env)
            good &= emit_checked(ctx, env, f"{client.alias} {s['customId']}")
        return good, envs

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
