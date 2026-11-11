"""pf_command: the decorator every pfcli command uses.

It declares a command's access and the PlayFab endpoints it calls, checks that against
ALLOWED_ENDPOINTS when the module loads, tags the help text, and gives every command that
changes something a --dry-run flag (passed to the function as dry_run).

Access levels:
  READ ONLY    reads PlayFab (or nothing) and changes nothing.
  READ WRITE   calls at least one PlayFab write endpoint; has --dry-run.
  LOCAL WRITE  calls no PlayFab endpoint but changes a local pfcli file; has --dry-run.
"""
import inspect

import click

from .client import ALLOWED_ENDPOINTS, WRITE

READ_ONLY, READ_WRITE, LOCAL_WRITE = "READ ONLY", "READ WRITE", "LOCAL WRITE"
ACCESS = (READ_ONLY, READ_WRITE, LOCAL_WRITE)


def pf_command(name: str, access: str, endpoints: tuple[str, ...] = (), notes: str = "",
               calls: str = ""):
    """notes: extra help text appended to the command's own (e.g. the shared explanation
    of player sessions on every client command). calls: text for the help's PlayFab line
    when the endpoints come from the config (checked at run time instead)."""
    if access not in ACCESS:
        raise ValueError(f"{name}: access must be one of {', '.join(ACCESS)}")
    for e in endpoints:
        if e not in ALLOWED_ENDPOINTS:
            raise ValueError(f"{name}: endpoint {e} is not registered in ALLOWED_ENDPOINTS")
    writes = [e for e in endpoints if ALLOWED_ENDPOINTS[e] == WRITE]
    if access == READ_ONLY and writes:
        raise ValueError(f"{name}: declared {READ_ONLY} but calls write endpoint(s) {', '.join(writes)}")
    if access == READ_WRITE and not writes:
        raise ValueError(f"{name}: declared {READ_WRITE} but calls no write endpoint")
    if access == LOCAL_WRITE and (endpoints or calls):
        raise ValueError(f"{name}: declared {LOCAL_WRITE} but calls PlayFab endpoints")

    def decorate(f):
        doc = inspect.cleandoc(f.__doc__ or "")
        first, _, rest = doc.partition("\n")
        line = calls or (", ".join(endpoints) if endpoints else "none (local only)")
        body = "\n\n".join(p for p in (rest.strip(), inspect.cleandoc(notes)) if p)
        f.__doc__ = f"[{access}] {first}\n\n\b\nAccess:   {access}\nPlayFab:  {line}\n\n{body}".rstrip()
        if access in (READ_WRITE, LOCAL_WRITE):
            what = "write requests" if access == READ_WRITE else "changes"
            f = click.option("--dry-run", is_flag=True,
                             help=f"Show the {what} instead of making them (reads still run).")(f)
        return click.command(name, short_help=f"[{access}] {first.rstrip('.')}")(f)

    return decorate
