import click

from ...pfcommand import LOCAL_WRITE, READ_ONLY, pf_command
from ...sessions import public

SELECT_HELP = """
\b
Selecting sessions:
  VALUE...      matches any session field: custom ID, PlayFab ID, title alias
                or title ID (case-insensitive). Several values widen the match.
  --title A     only sessions on title A (alias or ID); repeatable.
  --expired     only sessions older than ~24h or rejected by PlayFab.
Values and --title combine: both must match.
"""


def _select(store, values, titles, expired):
    return store.match(values, titles, expired)


@click.group("sessions")
def sessions():
    """Saved player sessions (local file, no PlayFab calls)."""


def selectors(f):
    f = click.option("--expired", is_flag=True, help="Only expired sessions.")(f)
    f = click.option("--title", "-t", "titles", multiple=True, help="Only these titles (alias or title ID).")(f)
    return click.argument("values", nargs=-1)(f)


@pf_command("list", READ_ONLY, notes=SELECT_HELP)
@selectors
@click.pass_context
def list_sessions(ctx, values, titles, expired):
    """List saved player sessions (tickets redacted).

    One output record per session: title, titleId, customId, playFabId, loggedInAt,
    newlyCreated, expired, and sessionTicket as <redacted>. The sessions file used is
    reported on stderr.
    """
    store = ctx.obj.sessions
    click.echo(f"sessions: {store.path}{'' if store.path.exists() else ' (none yet)'}", err=True)
    for s in _select(store, values, titles, expired):
        ctx.obj.emitter.emit(public(s))


@pf_command("flush", LOCAL_WRITE, notes=SELECT_HELP + """
\b
  --all         every session; required when no other selector is given.
\b
Flushing only stops pfcli from using a session. The ticket itself stays
valid at PlayFab until it expires (about 24 hours).
""")
@selectors
@click.option("--all", "flush_all", is_flag=True, help="Remove every saved session.")
@click.pass_context
def flush_sessions(ctx, values, titles, expired, flush_all, dry_run):
    """Remove saved player sessions.

    One output record per removed session (ticket redacted). With --dry-run, prints the
    sessions that would be removed and keeps them.
    """
    if not (values or titles or expired or flush_all):
        raise click.UsageError("say which sessions: VALUE..., --title, --expired, or --all")
    store = ctx.obj.sessions
    victims = store.sessions[:] if flush_all and not (values or titles or expired) else \
        _select(store, values, titles, expired)
    for s in victims:
        ctx.obj.emitter.emit({**public(s), **({"dryRun": True} if dry_run else {})})
    verb = "would remove" if dry_run else "removed"
    click.echo(f"{verb} {len(victims)} session(s) from {store.path}", err=True)
    if victims and not dry_run:
        store.remove(victims)
        store.save()
