import click

from ..pfcommand import READ_ONLY, pf_command


@pf_command("titles", READ_ONLY)
@click.pass_context
def titles(ctx):
    """List configured titles and whether each secret key is found (never prints keys).

    One output record per title: alias, titleId, host, key (set (file) / set (env) /
    EMPTY) and description. The config and secrets files used are reported on stderr.
    """
    cfg, emit = ctx.obj.config, ctx.obj.emitter.emit
    click.echo(f"config:  {cfg.path}\nsecrets: {cfg.secrets.path or 'none (environment only)'}", err=True)
    for alias in cfg.aliases():
        t = cfg.title(alias)
        emit({"alias": alias, "titleId": t["title_id"], "host": t["host"],
              "key": f"set ({t['key_source']})" if t["key"] else "EMPTY",
              "description": t.get("description", "")})
