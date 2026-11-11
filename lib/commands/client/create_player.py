import click

from ...client import PlayerClient, PlayFabError, error_text, ok
from ...config import ConfigError
from ...inputs import InputError, parse_vars
from ...pfcommand import READ_WRITE, pf_command
from ...sessions import redact
from . import sequences
from .common import SESSION_NOTES, var_option

SEQUENCE_NOTES = """
\b
Player sequences (config):
  A title can define how its players are created, updated and read, as
  ordered steps under player.create / player.update / player.state. A step
  runs a CloudScript function from the title's cloudscripts allow list, or
  calls a registered endpoint (Client steps as the player, Server/Admin
  steps with the title secret key). Steps stop at the first failure.
  Placeholders: $session, $playFabId, $customId, $titleId (from the
  session), $NAME and optional $NAME? (from --var NAME=VALUE).
"""


@pf_command("create-player", READ_WRITE, ("Client/LoginWithCustomID",),
            calls="Client/LoginWithCustomID, then the title's player.create steps",
            notes=SEQUENCE_NOTES + SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@click.option("--custom-id", "-u", "custom_ids", multiple=True, required=True,
              help="Custom ID for the new player (repeatable).")
@var_option
@click.pass_context
def create_player(ctx, aliases, custom_ids, var_pairs, dry_run):
    """Create players the way the title does (login + player.create steps).

    Logs in with CreateAccount, saves the session, then runs the title's player.create
    steps (if any). A custom ID that already has a player is not changed: use
    update-player for that. One output record per call; login tickets are <redacted>.
    --dry-run shows the login and every step without sending anything.
    """
    app = ctx.obj
    try:
        variables = parse_vars(var_pairs)
    except InputError as e:
        raise click.BadParameter(str(e), param_hint="--var")
    titles = []
    for alias in aliases:
        try:
            t = app.config.title(alias)
        except ConfigError as e:
            raise click.ClickException(str(e))
        titles.append((t, sequences.plan(t, "create", variables, required=False)))
    store = None if dry_run else app.sessions
    failed = False
    for title, steps in titles:
        client = PlayerClient(title)
        if not steps:
            click.echo(f"{client.alias}: no player.create steps in the config; creating the account only", err=True)
        for cid in (c.strip() for c in custom_ids):
            body = {"TitleId": title["title_id"], "CustomId": cid, "CreateAccount": True}
            try:
                env = client.call("Client/LoginWithCustomID", body, dry_run=dry_run)
            except PlayFabError as e:
                click.echo(f"{client.alias} {cid}: {e}", err=True)
                failed = True
                continue
            env.update({"customId": cid, "sequence": "player.create", "step": 0})
            app.emitter.emit(client.protect(redact(env)))
            if dry_run:
                sequences.run(ctx, title, client, None, steps, variables, "create")
                continue
            if not ok(env):
                click.echo(f"{client.alias} {cid}: {error_text(env)}", err=True)
                failed = True
                continue
            data = env["response"]["data"]
            store.put({"title": client.alias, "titleId": title["title_id"], "customId": cid,
                       "playFabId": data.get("PlayFabId"), "loggedInAt": env["at"],
                       "newlyCreated": bool(data.get("NewlyCreated")), "sessionTicket": data.get("SessionTicket")})
            store.save()
            if not data.get("NewlyCreated"):
                click.echo(f"{client.alias}: a player with custom ID '{cid}' already exists; nothing created "
                           f"(session saved; use update-player to change it)", err=True)
                failed = True
                continue
            click.echo(f"{client.alias}: created player {data.get('PlayFabId')} for custom ID '{cid}'", err=True)
            good, _ = sequences.run(ctx, title, client, store.get(title["title_id"], cid), steps, variables, "create")
            failed |= not good
    ctx.exit(1 if failed else 0)
