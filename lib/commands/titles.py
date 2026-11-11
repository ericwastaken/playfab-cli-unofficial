import json

import click

from ..pfcommand import READ_ONLY, pf_command


@pf_command("titles", READ_ONLY)
@click.pass_context
def titles(ctx):
    """List configured titles and whether each secret key is found (never prints keys)."""
    cfg = ctx.obj["config"]
    rows = []
    for alias in cfg.aliases():
        t = cfg.title(alias)
        rows.append({"alias": alias, "title_id": t["title_id"], "host": t["host"],
                     "key": f"set ({t['key_source']})" if t["key"] else "EMPTY",
                     "boards": {b: v.get("statistic") for b, v in t["boards"].items()},
                     "description": t.get("description", "")})
    if not ctx.obj["json_output"]:
        src = cfg.secrets.path or "none (environment only)"
        click.echo(f"config:  {cfg.path}\nsecrets: {src}")
    if ctx.obj["json_output"]:
        click.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    for r in rows:
        boards = ", ".join(f"{b}={s}" for b, s in r["boards"].items())
        click.echo(f"{r['alias']:<12} {r['title_id']:<9} key {r['key']:<10} {r['host']}  [{boards}]  {r['description']}")
