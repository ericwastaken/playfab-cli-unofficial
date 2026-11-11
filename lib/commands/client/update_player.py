import click

from ...config import ConfigError
from ...inputs import InputError, parse_vars
from ...pfcommand import READ_WRITE, pf_command
from . import sequences
from .common import SESSION_NOTES, custom_id_option, for_each_session, var_option
from .create_player import SEQUENCE_NOTES


@pf_command("update-player", READ_WRITE, ("Client/ExecuteCloudScript",),
            calls="the title's player.update steps (from the config)", notes=SEQUENCE_NOTES + SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@var_option
@click.pass_context
def update_player(ctx, aliases, custom_ids, var_pairs, dry_run):
    """Update logged-in players the way the title does (player.update steps).

    Runs the title's player.update steps as each player, e.g. a settings CloudScript
    with --var name=NewName. --dry-run sends nothing except steps that only read.
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
        plans[t["title_id"]] = (t, sequences.plan(t, "update", variables))

    def action(client, s):
        title, steps = plans[client.title_id]
        return sequences.run(ctx, title, client, s, steps, variables, "update", dry_run=dry_run)

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
