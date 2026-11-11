"""Shared pieces of the `client` commands: the two-step help text and session handling."""
import click

from ...client import PlayerClient, PlayFabError, session_expired
from ...config import ConfigError
from ...sessions import is_expired

LOGIN_CMD = "client login-with-custom-id"

# Appended to the --help of every client command.
SESSION_NOTES = f"""
\b
Player sessions (two steps):
  1. Log in once per player and title. This saves the player's session
     (ticket, PlayFab ID) in pfcli-sessions[-<client>].yml next to the config:
       pfcli --config ... {LOGIN_CMD} ALIAS --custom-id ID
  2. Run any client command as that player with the same --custom-id; it
     uses the saved session and never logs in by itself.
\b
A session lasts about 24 hours. A missing or expired session skips that
player and title with a message on stderr (exit status 1): log in again.
Client calls use no secret key, only the player's session, so they show
what a player (or anyone holding that player's ticket) can see and do.
List or remove saved sessions with: client sessions list | flush.
"""


def custom_id_option(f):
    return click.option("--custom-id", "-u", "custom_ids", multiple=True, required=True,
                        help="Custom ID of a logged-in player (repeatable); picks the saved session.")(f)


def for_each_session(ctx, aliases, custom_ids, action):
    """Run action(client, session) for every (title, custom ID) with a usable saved session.
    action returns the envelopes it produced; a session-expired reply marks the session
    expired. Returns True when everything succeeded."""
    app = ctx.obj
    store = app.sessions
    all_ok = True
    for alias in aliases:
        try:
            title = app.config.title(alias)
        except ConfigError as e:
            click.echo(f"{alias}: {e}; skipped", err=True)
            all_ok = False
            continue
        client = PlayerClient(title)
        for cid in (c.strip() for c in custom_ids):
            s = store.get(title["title_id"], cid)
            if not s:
                click.echo(f"{client.alias}: no saved session for custom ID '{cid}'; run: "
                           f"{LOGIN_CMD} {client.alias} --custom-id {cid}", err=True)
                all_ok = False
                continue
            if is_expired(s):
                click.echo(f"{client.alias}: session for '{cid}' has expired; log in again: "
                           f"{LOGIN_CMD} {client.alias} --custom-id {cid}", err=True)
                all_ok = False
                continue
            try:
                ok_, envs = action(client, s)
            except PlayFabError as e:
                click.echo(f"{client.alias} {cid}: {e}", err=True)
                all_ok = False
                continue
            all_ok &= ok_
            if any(session_expired(e) for e in envs if e):
                store.mark_expired(title["title_id"], cid)
                store.save()
                click.echo(f"{client.alias}: PlayFab rejected the session for '{cid}'; marked expired. "
                           f"Log in again: {LOGIN_CMD} {client.alias} --custom-id {cid}", err=True)
    return all_ok


def emit_checked(ctx, env, label) -> bool:
    from ...client import error_text, ok
    ctx.obj.emitter.emit(env)
    if not ok(env):
        click.echo(f"{label}: {error_text(env)}", err=True)
        return False
    return True


def function_failed(env) -> str | None:
    data = (env.get("response") or {}).get("data") or {}
    err = data.get("Error")
    if err:
        return f"CloudScript error: {err.get('Error')}: {err.get('Message')}"
    fr = data.get("FunctionResult")
    if isinstance(fr, dict) and (fr.get("errorCode") or (isinstance(fr.get("code"), int) and fr["code"] >= 400)
                                 or (fr.get("error") and ("errorMessage" in fr or "stack" in fr))):
        return f"function returned an error: {fr.get('error')}: {fr.get('errorMessage') or ''}".strip()
    return None


def var_option(f):
    return click.option("--var", "-V", "var_pairs", multiple=True, metavar="NAME=VALUE",
                        help="Value for a $NAME placeholder in the config's parameters or steps (repeatable).")(f)


def session_vars(s: dict, title_id: str) -> dict:
    """Reserved placeholder values for a saved session."""
    return {"session": s["sessionTicket"], "playFabId": s["playFabId"], "customId": s["customId"],
            "titleId": title_id}
