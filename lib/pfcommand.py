"""pf_command: the decorator every pfcli command uses.

It declares a command's access (READ ONLY or READ WRITE) and the PlayFab endpoints it
calls, checks that against ALLOWED_ENDPOINTS when the module loads, tags the help text,
and gives every READ WRITE command a --dry-run flag (passed to the function as dry_run).
"""
import inspect

import click

from .client import ALLOWED_ENDPOINTS, WRITE

READ_ONLY, READ_WRITE = "READ ONLY", "READ WRITE"


def pf_command(name: str, access: str, endpoints: tuple[str, ...] = ()):
    if access not in (READ_ONLY, READ_WRITE):
        raise ValueError(f"{name}: access must be {READ_ONLY!r} or {READ_WRITE!r}")
    for e in endpoints:
        if e not in ALLOWED_ENDPOINTS:
            raise ValueError(f"{name}: endpoint {e} is not registered in ALLOWED_ENDPOINTS")
    writes = [e for e in endpoints if ALLOWED_ENDPOINTS[e] == WRITE]
    if access == READ_ONLY and writes:
        raise ValueError(f"{name}: declared {READ_ONLY} but calls write endpoint(s) {', '.join(writes)}")
    if access == READ_WRITE and not writes:
        raise ValueError(f"{name}: declared {READ_WRITE} but calls no write endpoint")

    def decorate(f):
        doc = inspect.cleandoc(f.__doc__ or "")
        first, _, rest = doc.partition("\n")
        calls = ", ".join(endpoints) if endpoints else "none (local only)"
        f.__doc__ = f"[{access}] {first}\n\n\b\nAccess:   {access}\nPlayFab:  {calls}\n\n{rest.strip()}".rstrip()
        if access == READ_WRITE:
            f = click.option("--dry-run", is_flag=True,
                             help="Print the write requests instead of sending them (reads still run).")(f)
        return click.command(name, short_help=f"[{access}] {first.rstrip('.')}")(f)

    return decorate
