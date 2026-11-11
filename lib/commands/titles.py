import json
import os

import click


@click.command("titles")
@click.pass_context
def titles(ctx):
    """List configured titles and whether each secret key is set (never prints keys)."""
    cfg = ctx.obj["config"]
    rows = []
    for alias in cfg.aliases():
        t = cfg.title(alias)
        rows.append({"alias": alias, "title_id": t["title_id"], "host": t["host"],
                     "key_env": t["key_env"], "key": "set" if os.environ.get(t["key_env"], "").strip() else "EMPTY",
                     "boards": {b: v.get("statistic") for b, v in t["boards"].items()},
                     "description": t.get("description", "")})
    if ctx.obj["json_output"]:
        click.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    for r in rows:
        boards = ", ".join(f"{b}={s}" for b, s in r["boards"].items())
        click.echo(f"{r['alias']:<12} {r['title_id']:<9} key {r['key']:<5} {r['host']}  [{boards}]  {r['description']}")
