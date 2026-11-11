import copy
import json

import click

from ...client import ok
from ...config import ConfigError
from ...inputs import InputError, parse_vars, placeholders, resolve
from ...pfcommand import READ_WRITE, pf_command
from .common import (SESSION_NOTES, custom_id_option, emit_checked, for_each_session, function_failed,
                     session_vars, var_option)

CLOUDSCRIPT_NOTES = """
\b
Allowed functions (config):
  Only functions listed under the title's `cloudscripts` in the config (or
  under defaults.cloudscripts) can be run; anything else is refused before
  a request is sent. `pfcli titles` lists them per title, with the
  variables each one takes. Each entry can set:
    description  free text
    writes       true (default) or false: false marks a read-only function,
                 which still runs under --dry-run
    parameter    the FunctionParameter, with placeholders
\b
Placeholders in the parameter: $session, $playFabId, $customId, $titleId
are filled from the saved session; $NAME from --var NAME=VALUE (required);
$NAME? from --var if given, otherwise the field is left out. The session
ticket is never shown: it is <redacted> in the echoed request.
\b
A CloudScript error (data.Error) or a FunctionResult that looks like an
error (has errorCode, code >= 400, or error plus errorMessage/stack) is
reported on stderr and the exit status is 1; the full response is still
printed.
"""


@pf_command("execute-cloud-script", READ_WRITE, ("Client/ExecuteCloudScript",),
            notes=CLOUDSCRIPT_NOTES + SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@click.option("--function", "-f", "function_name", required=True,
              help="CloudScript function name; must be allowed for the title in the config.")
@var_option
@click.option("--params", "params_json", metavar="JSON",
              help="Override: extra FunctionParameter fields as a JSON object, merged over the "
                   "config's parameter (for one-off fields the config does not declare).")
@click.option("--revision", type=click.IntRange(min=0), default=None,
              help="Run this CloudScript revision instead of the live one.")
@click.option("--playstream-event", is_flag=True, help="Ask PlayFab to generate a PlayStream event for the call.")
@click.pass_context
def execute_cloud_script(ctx, aliases, custom_ids, function_name, var_pairs, params_json, revision,
                         playstream_event, dry_run):
    """Run an allowed CloudScript function as a logged-in player.

    Calls Client/ExecuteCloudScript (classic CloudScript) once per title and session.
    One output record per call holding PlayFab's own response (FunctionResult, Logs,
    Error, ...). READ WRITE: CloudScript can change anything the title's code allows, so
    --dry-run sends nothing, except functions the config marks writes: false.
    """
    app = ctx.obj
    try:
        variables = parse_vars(var_pairs)
    except InputError as e:
        raise click.BadParameter(str(e), param_hint="--var")
    extra = {}
    if params_json:
        try:
            extra = json.loads(params_json)
        except ValueError as e:
            raise click.BadParameter(f"not JSON: {e}", param_hint="--params")
        if not isinstance(extra, dict):
            raise click.BadParameter("must be a JSON object", param_hint="--params")
    # Check every title allows the function, and every placeholder has a value, before sending.
    specs = {}
    for alias in aliases:
        try:
            t = app.config.title(alias)
        except ConfigError as e:
            raise click.ClickException(str(e))
        allowed = t["cloudscripts"]
        if function_name not in allowed:
            names = ", ".join(sorted(allowed)) or "none (add a `cloudscripts` block to the title in the config)"
            raise click.ClickException(f"{t['alias']}: CloudScript function '{function_name}' is not allowed. "
                                       f"Allowed: {names}")
        spec = allowed[function_name]
        missing = []
        resolve({**spec["parameter"], **extra}, None,
                {**variables, **{k: "x" for k in ("session", "playFabId", "customId", "titleId")}}, missing)
        if missing:
            raise click.ClickException(
                f"{t['alias']} {function_name}: no value for {', '.join(sorted(set(missing)))}; use --var NAME=VALUE "
                f"(this function takes: {', '.join(placeholders(spec['parameter'])) or 'nothing'})")
        specs[t["title_id"]] = spec

    def action(client, s):
        spec = specs[client.title_id]
        param = resolve({**copy.deepcopy(spec["parameter"]), **extra}, None,
                        {**variables, **session_vars(s, client.title_id)})
        body = {"FunctionName": function_name, "FunctionParameter": param,
                "GeneratePlayStreamEvent": playstream_event}
        if revision is not None:
            body.update({"RevisionSelection": "Specific", "SpecificRevision": revision})
        env = client.call("Client/ExecuteCloudScript", body, s["sessionTicket"], dry_run=dry_run,
                          treat_as_read=not spec["writes"])
        env["customId"] = s["customId"]
        label = f"{client.alias} {s['customId']} {function_name}"
        good = emit_checked(ctx, env, label)
        if good and ok(env) and not env.get("dryRun"):
            failure = function_failed(env)
            if failure:
                click.echo(f"{label}: {failure}", err=True)
                good = False
        return good, [env]

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
