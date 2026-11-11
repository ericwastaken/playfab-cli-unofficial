import click

from ...client import PlayFabError, TitleClient, error_text, ok
from ...config import ConfigError
from ...inputs import InputError, build_bodies, gather_rows, load_template, parse_vars
from ...pfcommand import READ_ONLY, pf_command
from ..common import run_concurrent

DEFAULT_REQUEST = {
    "PlayFabId": "$.PlayFabId",
    "InfoRequestParameters": {"GetPlayerProfile": True, "ProfileConstraints": {"ShowDisplayName": True}},
}


@pf_command("get-player-combined-info", READ_ONLY, ("Server/GetPlayerCombinedInfo",))
@click.argument("aliases", nargs=-1, required=True)
@click.option("--playfab-id", "-p", "playfab_ids", multiple=True, help="Player's PlayFab ID (repeatable).")
@click.option("--input", "-i", "input_source", metavar="FILE|-",
              help="More rows: a CSV with a header, or NDJSON (e.g. pfcli output); '-' reads stdin.")
@click.option("--id-column", metavar="NAME",
              help="Input column holding the PlayFab ID; copied to PlayFabId. Default: PlayFabId.")
@click.option("--request", "-r", "request_spec", metavar="NAME|PATH",
              help="Request template (request-templates/NAME.yml) choosing what to fetch. "
                   "Default: profile with display name.")
@click.option("--var", "-V", "var_pairs", multiple=True, metavar="NAME=VALUE",
              help="Value for a $NAME placeholder in the request template (repeatable).")
@click.option("--concurrency", "-c", type=click.IntRange(1, 20), default=5, show_default=True,
              help="Requests in flight at once per title.")
@click.pass_context
def get_player_combined_info(ctx, aliases, playfab_ids, input_source, id_column, request_spec, var_pairs,
                             concurrency):
    """Read players' combined info (profile, data, statistics, ...) in bulk.

    Players come from --playfab-id and/or --input rows. For each title and each row, the
    request template is filled in ("$.<column>" takes that column's value) and sent; all
    bodies are built before any call, so a missing value stops the run first. One output
    record per player per title, holding PlayFab's own response, with the input row under
    "input" so formats can combine input columns with response fields.

    \b
    Default request (when --request is not given):
      PlayFabId: $.PlayFabId
      InfoRequestParameters:
        GetPlayerProfile: true
        ProfileConstraints: {ShowDisplayName: true}
    """
    app = ctx.obj
    cfg, emit = app.config, app.emitter.emit
    try:
        rows = gather_rows(playfab_ids, "PlayFabId", input_source, id_column)
        if not rows:
            raise click.UsageError("give at least one --playfab-id or an --input with rows")
        template = load_template(request_spec, DEFAULT_REQUEST, cfg.path.parent, app.root)
        bodies = build_bodies(template, rows, parse_vars(var_pairs))
    except InputError as e:
        raise click.ClickException(str(e))
    failed = False
    for alias in aliases:
        try:
            client = TitleClient(cfg.title(alias))
        except (ConfigError, PlayFabError) as e:
            click.echo(f"{alias}: {e}; skipped", err=True)
            failed = True
            continue

        def one(i):
            try:
                return client.call("Server/GetPlayerCombinedInfo", bodies[i]), None
            except PlayFabError as e:
                return None, e

        for i, (env, err) in enumerate(run_concurrent(one, list(range(len(bodies))), concurrency)):
            if err:
                click.echo(f"{client.alias} row {i + 1}: {err}", err=True)
                failed = True
                continue
            env["input"] = rows[i]
            emit(env)
            if not ok(env):
                click.echo(f"{client.alias} row {i + 1}: {error_text(env)}", err=True)
                failed = True
    ctx.exit(1 if failed else 0)
