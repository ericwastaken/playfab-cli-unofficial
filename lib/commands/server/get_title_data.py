import click

from ...client import PlayFabError, TitleClient, error_text, ok
from ...config import ConfigError
from ...pfcommand import READ_ONLY, pf_command


@pf_command("get-title-data", READ_ONLY, ("Server/GetTitleData",))
@click.argument("aliases", nargs=-1, required=True)
@click.option("--key", "-k", "keys", multiple=True, help="TitleData key to read (repeatable). Default: all keys.")
@click.pass_context
def get_title_data(ctx, aliases, keys):
    """Read TitleData key/value pairs for one or more titles.

    One output record per title holding PlayFab's own GetTitleData response
    (response.data.Data maps each key to its string value). Keys that do not exist are
    simply absent. For one row per key, use a format with rows: to_entries(response.data.Data).
    """
    cfg, emit = ctx.obj.config, ctx.obj.emitter.emit
    failed = False
    body = {"Keys": list(keys)} if keys else {}
    for alias in aliases:
        try:
            env = TitleClient(cfg.title(alias)).call("Server/GetTitleData", body)
        except (ConfigError, PlayFabError) as e:
            click.echo(f"{alias}: {e}; skipped", err=True)
            failed = True
            continue
        emit(env)
        if not ok(env):
            click.echo(f"{env['title']}: {error_text(env)}", err=True)
            failed = True
        elif keys:
            missing = [k for k in keys if k not in (env["response"]["data"].get("Data") or {})]
            if missing:
                click.echo(f"{env['title']}: key(s) not found: {', '.join(missing)}", err=True)
    ctx.exit(1 if failed else 0)
