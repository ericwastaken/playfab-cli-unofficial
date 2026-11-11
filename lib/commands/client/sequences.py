"""Player sequences from the title config: player.create / player.update / player.state.

A sequence is a list of steps, run in order as the logged-in player, stopping at the first
failure. A step is either a CloudScript function from the title's `cloudscripts` allow list
({cloudscript: NAME, parameter: {...}}) or a registered endpoint ({call: Family/Name,
body: {...}}); Client steps use the player's session, Server/Admin steps the title secret
key. Placeholders work as everywhere else ($session, $playFabId, $customId, $titleId,
$NAME / $NAME? from --var).
"""
import copy

import click

from ...client import ALLOWED_ENDPOINTS, WRITE, PlayerClient, PlayFabError, TitleClient, ok
from ...inputs import placeholders, resolve
from .common import emit_checked, function_failed, session_vars

RESERVED_DUMMY = {k: "x" for k in ("session", "playFabId", "customId", "titleId")}
DRY_SESSION = {"session": "<from login>", "playFabId": "<from login>", "customId": None, "titleId": None}


def plan(title: dict, role: str, variables: dict, read_only: bool = False, required: bool = True) -> list[dict]:
    """Check a title's sequence before anything is sent; return its steps ready to run."""
    seq = title["player"].get(role)
    if not seq:
        if required:
            raise click.ClickException(f"{title['alias']}: no player.{role} sequence in the config "
                                       f"(add player.{role}.steps to the title)")
        return []
    steps = []
    for i, st in enumerate(seq["steps"], 1):
        label = f"{title['alias']} player.{role} step {i}"
        if st.get("cloudscript"):
            name = st["cloudscript"]
            spec = title["cloudscripts"].get(name)
            if not spec:
                raise click.ClickException(f"{label}: CloudScript '{name}' is not in the title's cloudscripts "
                                           f"allow list")
            template = {**copy.deepcopy(spec["parameter"]), **copy.deepcopy(st.get("parameter") or {})}
            step = {"kind": "cloudscript", "name": name, "endpoint": "Client/ExecuteCloudScript",
                    "template": template, "writes": spec["writes"]}
        else:
            ep = st["call"]
            family = ep.split("/", 1)[0]
            if family in ("Server", "Admin") and not title.get("key"):
                raise click.ClickException(f"{label}: {ep} needs the title's secret key (not in the secrets file)")
            step = {"kind": "call", "name": ep, "endpoint": ep, "template": copy.deepcopy(st.get("body") or {}),
                    "writes": ALLOWED_ENDPOINTS[ep] == WRITE}
        if read_only and step["writes"]:
            raise click.ClickException(f"{label}: {step['name']} may write, but player.{role} must only read "
                                       f"(mark a read-only CloudScript with writes: false)")
        missing = []
        resolve(step["template"], None, {**variables, **RESERVED_DUMMY}, missing)
        if missing:
            raise click.ClickException(f"{label} ({step['name']}): no value for {', '.join(sorted(set(missing)))}; "
                                       f"use --var NAME=VALUE (takes: {', '.join(placeholders(step['template']))})")
        steps.append(step)
    return steps


def describe(title: dict) -> dict:
    """Short summary of a title's sequences for `titles`."""
    return {role: [f"{'cloudscript ' + s['cloudscript'] if s.get('cloudscript') else s['call']}"
                   for s in seq["steps"]] for role, seq in title["player"].items()}


def run(ctx, title: dict, client: PlayerClient, s: dict | None, steps: list[dict], variables: dict,
        role: str, dry_run: bool = False) -> tuple[bool, list]:
    """Run planned steps as the session's player. With s=None (a dry-run create, no session
    yet) nothing is sent: each step is shown as a dry-run record."""
    envs = []
    for i, step in enumerate(steps, 1):
        vals = {**variables, **(session_vars(s, client.title_id) if s else {**DRY_SESSION, "titleId": client.title_id})}
        body = resolve(step["template"], None, vals)
        if step["kind"] == "cloudscript":
            body = {"FunctionName": step["name"], "FunctionParameter": body, "GeneratePlayStreamEvent": False}
        label = f"{client.alias} {s['customId'] if s else ''} player.{role} step {i} {step['name']}".replace("  ", " ")
        try:
            if s is None:
                env = {**client._envelope(step["endpoint"], body), "dryRun": True, "response": None}
            elif step["endpoint"].startswith("Client/"):
                env = client.call(step["endpoint"], body, s["sessionTicket"], dry_run=dry_run,
                                  treat_as_read=not step["writes"])
            else:
                tc = TitleClient(title)
                env = tc.protect(tc.call(step["endpoint"], body, dry_run=dry_run), s["sessionTicket"])
        except PlayFabError as e:
            click.echo(f"{label}: {e}", err=True)
            return False, envs
        env.update({"customId": s["customId"] if s else None, "sequence": f"player.{role}", "step": i})
        envs.append(env)
        if not emit_checked(ctx, env, label):
            return False, envs
        if step["kind"] == "cloudscript" and ok(env) and not env.get("dryRun"):
            failure = function_failed(env)
            if failure:
                click.echo(f"{label}: {failure}", err=True)
                return False, envs
    return True, envs
