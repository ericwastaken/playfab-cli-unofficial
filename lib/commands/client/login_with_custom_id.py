import click

from ...client import PlayerClient, PlayFabError, error_text, ok
from ...config import ConfigError
from ...inputs import InputError, gather_rows
from ...pfcommand import READ_WRITE, pf_command
from ...sessions import redact
from .common import SESSION_NOTES


@pf_command("login-with-custom-id", READ_WRITE, ("Client/LoginWithCustomID",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@click.option("--custom-id", "-u", "custom_ids", multiple=True, help="Custom ID to log in as (repeatable).")
@click.option("--input", "-i", "input_source", metavar="FILE|-",
              help="More custom IDs: a CSV with a header, or NDJSON; '-' reads stdin.")
@click.option("--id-column", metavar="NAME", help="Input column holding the custom ID. Default: CustomId.")
@click.option("--create-account", is_flag=True,
              help="Create the player if the custom ID is new (PlayFab CreateAccount). "
                   "Without it, an unknown custom ID fails with AccountNotFound. On a title "
                   "with a player.create sequence, use `client create-player` instead.")
@click.option("--skip-create-steps", is_flag=True,
              help="Allow --create-account on a title that has a player.create sequence, "
                   "creating a bare account without running those steps.")
@click.pass_context
def login_with_custom_id(ctx, aliases, custom_ids, input_source, id_column, create_account,
                         skip_create_steps, dry_run):
    """Log in players by custom ID and save their sessions (step 1 of 2).

    Calls Client/LoginWithCustomID for each title and custom ID and saves the session for
    later client commands. One output record per login holding PlayFab's own response,
    with SessionTicket and EntityToken shown as <redacted> (tickets are credentials; the
    real ticket is kept only in the sessions file).

    This is READ WRITE: --create-account can create players, and any login can trigger
    the title's login automations or CloudScript. --dry-run shows the requests without
    sending them (no session is saved).
    """
    app = ctx.obj
    try:
        rows = gather_rows(custom_ids, "CustomId", input_source, id_column)
    except InputError as e:
        raise click.ClickException(str(e))
    rows = [r for r in rows if str(r.get("CustomId") or "").strip()]
    if not rows:
        raise click.UsageError("give at least one --custom-id or an --input with custom IDs")
    if create_account and not skip_create_steps:
        for alias in aliases:
            try:
                t = app.config.title(alias)
            except ConfigError as e:
                raise click.ClickException(str(e))
            if t["player"].get("create"):
                raise click.ClickException(
                    f"{t['alias']} defines how its players are created (player.create in the config). "
                    f"Use: client create-player {t['alias']} --custom-id ID ... "
                    f"(or add --skip-create-steps for a bare account)")
    store = None if dry_run else app.sessions
    failed = False
    for alias in aliases:
        try:
            title = app.config.title(alias)
        except ConfigError as e:
            click.echo(f"{alias}: {e}; skipped", err=True)
            failed = True
            continue
        client = PlayerClient(title)
        for row in rows:
            cid = str(row["CustomId"]).strip()
            body = {"TitleId": title["title_id"], "CustomId": cid, "CreateAccount": create_account}
            try:
                env = client.call("Client/LoginWithCustomID", body, dry_run=dry_run)
            except PlayFabError as e:
                click.echo(f"{client.alias} {cid}: {e}", err=True)
                failed = True
                continue
            if input_source:
                env["input"] = row
            app.emitter.emit(client.protect(redact(env)))
            if not ok(env):
                click.echo(f"{client.alias} {cid}: {error_text(env)}", err=True)
                failed = True
                continue
            if dry_run:
                continue
            data = env["response"]["data"]
            store.put({"title": client.alias, "titleId": title["title_id"], "customId": cid,
                       "playFabId": data.get("PlayFabId"), "loggedInAt": env["at"],
                       "newlyCreated": bool(data.get("NewlyCreated")),
                       "sessionTicket": data.get("SessionTicket")})
            store.save()
            if data.get("NewlyCreated"):
                click.echo(f"{client.alias}: created new player for custom ID '{cid}'", err=True)
    ctx.exit(1 if failed else 0)
