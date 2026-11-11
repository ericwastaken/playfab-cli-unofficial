"""`pfcli init`: create (or extend) a config + secrets pair for a project.

Creates pfcli-config-<name>.yml and pfcli-secrets-<name>.yml. The secrets file gets one
empty slot per title ID and is created chmod 600; keys are never accepted as options (they
would end up in shell history and agent transcripts): the user pastes them in an editor.
With --add-title, titles are appended to an existing pair as text, so comments and YAML
anchors survive. Every change is validated by loading the result before it is kept.
"""
import os
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import click
import yaml

from ..config import Config, ConfigError, Secrets
from ..pfcommand import LOCAL_WRITE, pf_command

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,40}$")
TITLE_ID_RE = re.compile(r"^[0-9A-Fa-f]{4,10}$")
GUIDE = "https://ericwastaken.github.io/playfab-cli-unofficial"
KEY_HELP = ("# For each title: Game Manager > the title > Settings (gear) > Title settings > Secret Keys >\n"
            "# New secret key (name it e.g. \"pfcli\"), then paste the key between the quotes below.\n"
            "# A secret key is full access to the title: never commit, share or paste it anywhere else.\n")


def _pairs(values, what):
    out = {}
    for v in values:
        k, sep, val = v.partition("=")
        if not sep or not k or not val:
            raise click.BadParameter(f"expected ALIAS=VALUE, got '{v}'", param_hint=what)
        out[k] = val
    return out


def _parse_titles(values, descriptions, hosts):
    titles = _pairs(values, "--title / --add-title")
    for alias, tid in titles.items():
        if not ALIAS_RE.match(alias):
            raise click.BadParameter(f"alias '{alias}': use letters, digits, '-' or '_'", param_hint="--title")
        if not TITLE_ID_RE.match(tid):
            raise click.BadParameter(f"title ID '{tid}' for {alias}: PlayFab title IDs are 4-10 hex characters "
                                     f"(Game Manager > title > Settings > Title settings)", param_hint="--title")
    desc, host = _pairs(descriptions, "--description"), _pairs(hosts, "--host")
    for extra, opt in ((desc, "--description"), (host, "--host")):
        unknown = set(extra) - set(titles)
        if unknown:
            raise click.BadParameter(f"{', '.join(sorted(unknown))} not given with --title/--add-title",
                                     param_hint=opt)
    for alias, h in host.items():
        if not h.startswith(("https://", "http://")):
            raise click.BadParameter(f"host for {alias} must start with https://", param_hint="--host")
        if h.startswith("http://"):
            click.echo(f"warning: host for {alias} is not https", err=True)
    return {a: {"title_id": t.upper(), "description": desc.get(a), "host": host.get(a)} for a, t in titles.items()}


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _config_entries(titles: dict) -> str:
    out = []
    for alias, t in titles.items():
        out.append(f"  {alias}:\n    title_id: {_q(t['title_id'])}\n")
        if t["description"]:
            out.append(f"    description: {_q(t['description'])}\n")
        if t["host"]:
            out.append(f"    host: {_q(t['host'])}   # dedicated cluster\n")
    return "".join(out)


def _secret_entries(titles: dict) -> str:
    return "".join(f'  {_q(t["title_id"])}: ""   # {alias}\n' for alias, t in titles.items())


def _new_config(name: str, titles: dict) -> str:
    head = (f"# pfcli config for '{name}' (gitignored). Created by `pfcli init` on {date.today()}.\n"
            f"# Secret keys are NOT here: they go in pfcli-secrets-{name}.yml (same folder), by title ID.\n"
            f"# Reference: {GUIDE}/reference/configuration/\n"
            "defaults:\n  host: \"https://{title_id}.playfabapi.com\"\n\ntitles:\n")
    if titles:
        return head + _config_entries(titles)
    return head + ("  # Add one entry per title (then run: pfcli init " + name + " --add-title ALIAS=TITLE_ID):\n"
                   "  # GAME-DEV:\n  #   title_id: \"ABCD2\"     # Game Manager > title > Settings > Title settings\n"
                   "  #   description: \"Our game, dev\"\n"
                   "  #   host: \"https://{title_id}.your-cluster.playfabapi.com\"   # only for dedicated clusters\n")


def _new_secrets(name: str, titles: dict) -> str:
    return (f"# pfcli secret keys for '{name}' (gitignored, chmod 600). Created by `pfcli init` on {date.today()}.\n"
            + KEY_HELP + "titles:\n" + (_secret_entries(titles) if titles else
                                        '  # "ABCD2": ""   # GAME-DEV\n'))


def _insert_into_titles(text: str, block: str) -> str:
    """Insert block at the end of the top-level `titles:` section (before the next top-level key)."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if re.match(r"^titles:\s*(#.*)?$", l)), None)
    if start is None:
        return text.rstrip("\n") + "\n\ntitles:\n" + block
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^[^\s#]", lines[i]):
            end = i
            break
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    if lines[end - 1] and not lines[end - 1].endswith("\n"):
        lines[end - 1] += "\n"
    return "".join(lines[:end]) + block + "".join(lines[end:])


def _write(path: Path, text: str, secret: bool):
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if secret else 0o644)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, path)
    if secret:
        os.chmod(path, 0o600)


def _git_ignored(path: Path) -> bool | None:
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=path.parent, capture_output=True)
    except OSError:
        return None
    return {0: True, 1: False}.get(r.returncode)  # 128 = not a git repo


@pf_command("init", LOCAL_WRITE, notes=f"""
\b
Examples:
  pfcli init acme --title GAME-DEV=ABCD2 --title GAME-PROD=ABCD1 \\
      --description GAME-DEV="Our game, dev"
  pfcli init acme --add-title GAME-STAGE=ABCD3
\b
Where the facts are: the title ID is on the title's card in Game Manager,
in its URL (.../t/TITLE_ID/...) and under Settings > Title settings. If
your Game Manager address is developer.<cluster>.playfab.com, the title is
on a dedicated cluster: add --host ALIAS=https://{{title_id}}.<cluster>.playfabapi.com
\b
Keys are never taken as options. After init, open the secrets file in
your editor, paste each title's secret key, then run: pfcli titles --verify
Guide: {GUIDE}/getting-started/setup/
""")
@click.argument("name")
@click.option("--title", "titles_opt", multiple=True, metavar="ALIAS=TITLE_ID",
              help="A title for a NEW pair (repeatable).")
@click.option("--add-title", "add_opt", multiple=True, metavar="ALIAS=TITLE_ID",
              help="Add a title to an EXISTING pair (repeatable).")
@click.option("--description", multiple=True, metavar="ALIAS=TEXT", help="Description for a title (repeatable).")
@click.option("--host", multiple=True, metavar="ALIAS=URL",
              help="API host for a title on a dedicated cluster (repeatable).")
@click.option("--dir", "directory", type=click.Path(file_okay=False, path_type=Path), default=None,
              help="Folder for the files. Default: the pfcli home folder ($PFCLI_HOME, or the current folder).")
@click.option("--force", is_flag=True, help="Overwrite an existing pair (new pair only).")
@click.pass_context
def init(ctx, name, titles_opt, add_opt, description, host, directory, force, dry_run):
    """Create a config + secrets pair for a project (or add titles to one).

    Writes pfcli-config-NAME.yml and pfcli-secrets-NAME.yml. The secrets file is created
    chmod 600 with an empty slot per title ID; paste the keys in your editor. One output
    record per file (with --dry-run: the content that would be written).
    """
    if not NAME_RE.match(name):
        raise click.BadParameter("use lowercase letters, digits and '-' (e.g. acme)", param_hint="NAME")
    if titles_opt and add_opt:
        raise click.UsageError("use --title for a new pair, or --add-title for an existing one, not both")
    d = (directory or ctx.obj.root).expanduser()
    cfg_path, sec_path = d / f"pfcli-config-{name}.yml", d / f"pfcli-secrets-{name}.yml"
    emit = ctx.obj.emitter.emit
    adding = bool(add_opt)
    titles = _parse_titles(add_opt or titles_opt, description, host)

    if adding:
        if not cfg_path.exists():
            raise click.ClickException(f"{cfg_path} does not exist: create it first with pfcli init {name} --title ...")
        raw = yaml.safe_load(cfg_path.read_text()) or {}
        have_aliases = {str(a).lower() for a in (raw.get("titles") or {})}
        clash = [a for a in titles if a.lower() in have_aliases]
        if clash:
            raise click.ClickException(f"title(s) already in {cfg_path.name}: {', '.join(sorted(clash))}")
        new_cfg = _insert_into_titles(cfg_path.read_text(), _config_entries(titles))
        if sec_path.exists():
            sraw = yaml.safe_load(sec_path.read_text()) or {}
            have = {str(k).upper() for k in (sraw.get("titles") or {})}
            todo = {a: t for a, t in titles.items() if t["title_id"] not in have}
            new_sec = _insert_into_titles(sec_path.read_text(), _secret_entries(todo)) if todo else None
        else:
            new_sec = _new_secrets(name, titles)
    else:
        existing = [p for p in (cfg_path, sec_path) if p.exists()]
        if existing and not force:
            raise click.ClickException(f"{', '.join(p.name for p in existing)} already exist(s): use --add-title to "
                                       f"add titles, or --force to overwrite")
        new_cfg, new_sec = _new_config(name, titles), _new_secrets(name, titles)

    # Validate what would be written before keeping it (a config with no titles yet is allowed).
    if titles:
        fd, tmp_name = tempfile.mkstemp(suffix=".yml", prefix="pfcli-init-check-")
        tmp_cfg = Path(tmp_name)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(new_cfg)
            Config(tmp_cfg, Secrets(None))
        except (ConfigError, yaml.YAMLError) as e:
            raise click.ClickException(f"the result would not load, nothing written: {e}")
        finally:
            tmp_cfg.unlink(missing_ok=True)

    plan = [(cfg_path, new_cfg, False), (sec_path, new_sec, True)]
    for path, text, secret in plan:
        if text is None:
            emit({"file": str(path), "action": "unchanged", "titles": list(titles)})
            continue
        action = ("updated" if adding and path.exists() else "created")
        if dry_run:
            emit({"file": str(path), "action": f"would be {action}", "content": text, "dryRun": True})
            continue
        d.mkdir(parents=True, exist_ok=True)
        _write(path, text, secret)
        emit({"file": str(path), "action": action, "titles": list(titles)})
    if dry_run:
        return
    for path in (cfg_path, sec_path):
        if _git_ignored(path) is False:
            click.echo(f"WARNING: Git would NOT ignore {path}. Keep it out of commits (move it, or rename it "
                       f"to match pfcli's ignore patterns).", err=True)
    ids = ", ".join(f"{t['title_id']} ({a})" for a, t in titles.items()) or "(none yet)"
    click.echo(f"\nNext steps:\n  1. Open {sec_path} in your editor and paste the secret key for each title ID: {ids}.\n"
               f"     (Game Manager > the title > Settings > Title settings > Secret Keys.) Never paste keys in chat.\n"
               f"  2. Check: pfcli --config {cfg_path} titles --verify", err=True)
