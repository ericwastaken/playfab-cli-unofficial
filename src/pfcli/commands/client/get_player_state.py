import click

from ...config import ConfigError
from ...inputs import InputError, parse_vars
from ...pfcommand import READ_ONLY, pf_command
from . import sequences
from .common import SESSION_NOTES, custom_id_option, for_each_session, var_option
from .create_player import SEQUENCE_NOTES


@pf_command("get-player-state", READ_ONLY,
            calls="the title's player.state steps (from the config; reads only, checked before sending)",
            notes=SEQUENCE_NOTES + SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@var_option
@click.pass_context
def get_player_state(ctx, aliases, custom_ids, var_pairs):
    """Read logged-in players' state the way the title does (player.state steps).

    Every step of player.state must be a read: a read endpoint, or a CloudScript the
    config marks writes: false. Anything else is refused before a request is sent.
    """
    app = ctx.obj
    try:
        variables = parse_vars(var_pairs)
    except InputError as e:
        raise click.BadParameter(str(e), param_hint="--var")
    plans = {}
    for alias in aliases:
        try:
            t = app.config.title(alias)
        except ConfigError as e:
            raise click.ClickException(str(e))
        plans[t["title_id"]] = (t, sequences.plan(t, "state", variables, read_only=True))

    def action(client, s):
        title, steps = plans[client.title_id]
        return sequences.run(ctx, title, client, s, steps, variables, "state")

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
