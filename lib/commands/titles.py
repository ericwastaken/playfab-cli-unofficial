import click

from ..client import PlayFabError, TitleClient, ok
from ..inputs import placeholders
from ..pfcommand import READ_ONLY, pf_command
from .client.sequences import describe

VERIFY_KEY = "__pfcli_verify__"  # a TitleData key that does not exist: nothing real is read


def verify(t: dict) -> str:
    """One harmless live read proving the host and secret key work for a title."""
    if not t["key"]:
        return "skipped: no secret key (client-only use needs none)"
    try:
        env = TitleClient(t).call("Server/GetTitleData", {"Keys": [VERIFY_KEY]})
    except PlayFabError as e:
        return f"error: cannot reach {t['host']}: {e}"
    if ok(env):
        return "ok"
    r = env.get("response") or {}
    err = r.get("error") or r.get("status")
    if err == "InvalidAPIEndpoint":
        return ("error: InvalidAPIEndpoint: the title is on a dedicated cluster, or the title ID is wrong. "
                "Set its host in the config")
    if r.get("code") in (401, 403) or err in ("NotAuthenticated", "InvalidSecretKey", "NotAuthorized"):
        return f"error: {err}: the secret key was rejected (wrong key, disabled, or for another title)"
    return f"error: {r.get('code')} {err}: {r.get('errorMessage') or ''}".strip()


@pf_command("titles", READ_ONLY, ("Server/GetTitleData",),
            calls="none (with --verify: one harmless Server/GetTitleData per title)")
@click.option("--verify", "do_verify", is_flag=True,
              help="Make one harmless live call per title to prove its host and secret key work.")
@click.pass_context
def titles(ctx, do_verify):
    """List configured titles and whether each secret key is found (never prints keys).

    One output record per title: alias, titleId, host, key (set (file) / set (env) /
    EMPTY), the CloudScript functions allowed for client execute-cloud-script (with the
    placeholders each takes), the player sequences, and description. The config and
    secrets files used are reported on stderr. With --verify, each record also has
    "verify": "ok" or the problem and how to fix it; exit status 1 if any title failed.
    """
    cfg, emit = ctx.obj.config, ctx.obj.emitter.emit
    click.echo(f"config:  {cfg.path}\nsecrets: {cfg.secrets.path or 'none (environment only)'}", err=True)
    failed = False
    for alias in cfg.aliases():
        t = cfg.title(alias)
        rec = {"alias": alias, "titleId": t["title_id"], "host": t["host"],
               "key": f"set ({t['key_source']})" if t["key"] else "EMPTY",
               "cloudscripts": {n: {"writes": s["writes"], "takes": placeholders(s["parameter"])}
                                for n, s in sorted(t["cloudscripts"].items())},
               "player": describe(t),
               "description": t.get("description", "")}
        if do_verify:
            rec["verify"] = verify(t)
            if rec["verify"].startswith("error"):
                failed = True
                click.echo(f"{alias}: {rec['verify']}", err=True)
        emit(rec)
    ctx.exit(1 if failed else 0)
