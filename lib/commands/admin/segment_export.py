"""Segment exports: start, wait for, and download PlayFab's asynchronous segment exports.

PlayFab flow: Admin/ExportPlayersInSegment -> {ExportId}; Admin/GetSegmentExport -> {State}
until done, then {IndexUrl}; the index file lists the URLs of the profile-data files. Those
links are usually pre-signed (the query string grants access), so they are only ever used
here to download, and are redacted everywhere else (output, logs, messages).
"""
import gzip
import json
import logging
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import click

from ...client import PlayFabError, TitleClient, error_text, ok, redact_url
from ...config import ConfigError
from ...pfcommand import READ_ONLY, pf_command

logger = logging.getLogger("pfcli")
FAILED_STATES = {"failed", "error", "errored", "canceled", "cancelled", "aborted"}
EXPORTS_DIR = "pfcli-exports"

FILES_NOTES = """
\b
Download: writes the index file and every data file into --dir (default:
pfcli-exports/<ALIAS>-<EXPORT_ID>/ in the pfcli folder, which Git ignores).
Existing files are never overwritten. The files are PLAYER DATA: keep them
private and delete them when done. The download links PlayFab returns are
pre-signed (they grant access by themselves), so pfcli never prints them:
their query strings show as <redacted>.
"""


def _git_ignored(path: Path):
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=path.parent if path.parent.exists() else None,
                           capture_output=True)
    except OSError:
        return None
    return {0: True, 1: False}.get(r.returncode)


def wait_for_export(client: TitleClient, export_id: str, timeout: int, poll: int, emit):
    """Poll GetSegmentExport until it has an IndexUrl, fails, or times out.
    Returns (raw reply or None, protected envelope or None, status text)."""
    start = time.monotonic()
    last_state = None
    while True:
        raw, env = client.call_raw("Admin/GetSegmentExport", {"ExportId": export_id})
        if not ok(env):
            emit(env)
            return None, env, f"error: {error_text(env)}"
        data = raw.get("data") or {}
        state = str(data.get("State") or "")
        if data.get("IndexUrl"):
            emit(env)
            return raw, env, "complete"
        if state.lower() in FAILED_STATES:
            emit(env)
            return None, env, f"error: export {state}"
        if state != last_state:
            click.echo(f"{client.alias} export {export_id}: {state or 'pending'}", err=True)
            last_state = state
        if time.monotonic() - start + poll > timeout:
            emit(env)
            return None, env, f"timeout: still {state or 'pending'} after {timeout}s (check later with: " \
                              f"admin get-segment-export {client.alias} --export-id {export_id})"
        time.sleep(poll)


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url), timeout=120) as r:
        return r.read()


def _safe_name(url: str, fallback: str) -> str:
    name = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or fallback


def _urls_in_index(content: bytes) -> list[str]:
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    text = content.decode("utf-8", errors="replace")
    urls = []
    try:
        def walk(v):
            if isinstance(v, str) and v.startswith(("http://", "https://")):
                urls.append(v)
            elif isinstance(v, dict):
                for x in v.values():
                    walk(x)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
        walk(json.loads(text))
    except ValueError:
        urls = re.findall(r"https?://[^\s\"'<>,]+", text)
    return list(dict.fromkeys(urls))


def download_export(index_url: str, out_dir: Path) -> dict:
    """Download the index and every file it lists into out_dir (never overwriting)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        index = _fetch(index_url)
    except (urllib.error.URLError, TimeoutError) as e:
        raise PlayFabError(f"could not download the export index ({redact_url(index_url)}): {e}")
    index_name = _safe_name(index_url, "index")
    index_path = out_dir / index_name
    if index_path.exists():
        raise PlayFabError(f"{index_path} already exists; choose another --dir")
    index_path.write_bytes(index)
    files, total = [], 0
    for i, url in enumerate(_urls_in_index(index), 1):
        path = out_dir / _safe_name(url, f"part-{i:04d}")
        if path.exists():
            path = out_dir / f"{i:04d}-{path.name}"
        if path.exists():
            raise PlayFabError(f"{path} already exists; choose another --dir")
        try:
            data = _fetch(url)
        except (urllib.error.URLError, TimeoutError) as e:
            raise PlayFabError(f"could not download {redact_url(url)}: {e}")
        path.write_bytes(data)
        files.append({"name": path.name, "bytes": len(data)})
        total += len(data)
        click.echo(f"  downloaded {path.name} ({len(data)} bytes)", err=True)
    return {"dir": str(out_dir), "index": index_name, "files": files, "totalBytes": total}


def _default_dir(root: Path, alias: str, export_id: str) -> Path:
    return root / EXPORTS_DIR / f"{alias}-{export_id}"


def _download_and_emit(ctx, client, raw, export_id, directory):
    out_dir = (directory.expanduser() if directory else _default_dir(ctx.obj.root, client.alias, export_id))
    if out_dir.exists() and any(out_dir.iterdir()):
        raise PlayFabError(f"{out_dir} is not empty; choose another --dir")
    result = download_export(raw["data"]["IndexUrl"], out_dir)
    ctx.obj.emitter.emit({"title": client.alias, "titleId": client.title_id, "exportId": export_id, **result})
    if _git_ignored(out_dir / result["index"]) is False:
        click.echo(f"WARNING: Git would NOT ignore {out_dir}. These files are player data: keep them out of "
                   f"commits.", err=True)
    click.echo(f"{client.alias}: {len(result['files'])} file(s), {result['totalBytes']} bytes in {out_dir} "
               f"(player data: keep private, delete when done)", err=True)


def _wait_opts(f):
    f = click.option("--poll", type=click.IntRange(2, 300), default=10, show_default=True,
                     help="Seconds between status checks.")(f)
    f = click.option("--timeout", type=click.IntRange(10, 86400), default=900, show_default=True,
                     help="Give up waiting after this many seconds.")(f)
    return f


@pf_command("export-players-in-segment", READ_ONLY, ("Admin/ExportPlayersInSegment", "Admin/GetSegmentExport"),
            notes=FILES_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@click.option("--segment-id", required=True, help="Segment ID (from admin get-all-segments).")
@click.option("--wait", "do_wait", is_flag=True, help="Wait until the export is ready (polls get-segment-export).")
@_wait_opts
@click.option("--download", "download", is_flag=True, help="Wait, then download the export files (implies --wait).")
@click.option("--dir", "directory", type=click.Path(file_okay=False, path_type=Path), default=None,
              help="Download folder (with --download).")
@click.pass_context
def export_players_in_segment(ctx, aliases, segment_id, do_wait, poll, timeout, download, directory):
    """Export all players in a segment (asynchronous), optionally wait and download.

    PlayFab takes a snapshot of every player profile in the segment and prepares it as
    files in the background. Without --wait, this starts the export and prints its
    ExportId (check it later with admin get-segment-export, download it with admin
    download-segment-export). With --wait, it polls until ready (or --timeout); with
    --download, it then downloads the files. Starting an export changes no game data.
    """
    app = ctx.obj
    failed = False
    for alias in aliases:
        try:
            client = TitleClient(app.config.title(alias))
            env = client.call("Admin/ExportPlayersInSegment", {"SegmentId": segment_id})
        except (ConfigError, PlayFabError) as e:
            click.echo(f"{alias}: {e}; skipped", err=True)
            failed = True
            continue
        app.emitter.emit(env)
        if not ok(env):
            click.echo(f"{client.alias}: {error_text(env)}", err=True)
            failed = True
            continue
        export_id = env["response"]["data"].get("ExportId")
        click.echo(f"{client.alias}: export started, ExportId {export_id}", err=True)
        if not (do_wait or download):
            continue
        try:
            raw, _, status = wait_for_export(client, export_id, timeout, poll, app.emitter.emit)
            if status != "complete":
                click.echo(f"{client.alias}: {status}", err=True)
                failed = True
                continue
            if download:
                _download_and_emit(ctx, client, raw, export_id, directory)
        except PlayFabError as e:
            click.echo(f"{client.alias}: {e}", err=True)
            failed = True
    ctx.exit(1 if failed else 0)


@pf_command("download-segment-export", READ_ONLY, ("Admin/GetSegmentExport",), notes=FILES_NOTES)
@click.argument("alias")
@click.option("--export-id", required=True, help="ExportId from export-players-in-segment.")
@_wait_opts
@click.option("--dir", "directory", type=click.Path(file_okay=False, path_type=Path), default=None,
              help="Download folder.")
@click.pass_context
def download_segment_export(ctx, alias, export_id, poll, timeout, directory):
    """Download a finished segment export (waits if it is still running).

    Checks the export with Admin/GetSegmentExport, waits up to --timeout while it is still
    being prepared, then downloads the index file and every data file it lists.
    """
    app = ctx.obj
    try:
        client = TitleClient(app.config.title(alias))
        raw, _, status = wait_for_export(client, export_id, timeout, poll, app.emitter.emit)
        if status != "complete":
            raise click.ClickException(f"{client.alias}: {status}")
        _download_and_emit(ctx, client, raw, export_id, directory)
    except (ConfigError, PlayFabError) as e:
        raise click.ClickException(str(e))
