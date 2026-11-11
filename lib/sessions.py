"""Saved player sessions for Client API commands.

`client login-with-custom-id` saves one session per (title ID, custom ID): the session
ticket, the player's PlayFab ID and the login time. Every other `client` command looks the
session up by title and --custom-id. The file is YAML, written chmod 600, and paired with
the config like the secrets file: pfcli-config[-<client>].yml -> pfcli-sessions[-<client>].yml.
Session tickets are credentials: never print them (see redact()).
"""
import copy
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

logger = logging.getLogger("pfcli")

TICKET_LIFETIME = timedelta(hours=24)  # PlayFab session tickets last about 24 hours
REDACTED = "<redacted>"


def paired_sessions_path(config_path: Path) -> Path:
    """pfcli-config[-<client>].yml -> pfcli-sessions[-<client>].yml; any other config name
    -> pfcli-sessions.yml next to it."""
    name = config_path.name
    if name.startswith("pfcli-config"):
        return config_path.with_name("pfcli-sessions" + name[len("pfcli-config"):])
    return config_path.with_name("pfcli-sessions.yml")


def _parse_time(s: str | None):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def is_expired(s: dict) -> bool:
    if s.get("expired"):
        return True
    t = _parse_time(s.get("loggedInAt"))
    return t is None or datetime.now(timezone.utc) - t > TICKET_LIFETIME


def public(s: dict) -> dict:
    """A session as printable output: ticket redacted, plus age and expiry."""
    out = {k: v for k, v in s.items() if k != "sessionTicket"}
    out["sessionTicket"] = REDACTED
    out["expired"] = is_expired(s)
    return out


def redact(env: dict) -> dict:
    """Copy of a login envelope with SessionTicket and EntityToken redacted."""
    env = copy.deepcopy(env)
    data = (env.get("response") or {}).get("data") or {}
    if "SessionTicket" in data:
        data["SessionTicket"] = REDACTED
    tok = data.get("EntityToken")
    if isinstance(tok, dict) and "EntityToken" in tok:
        tok["EntityToken"] = REDACTED
    return env


class SessionStore:
    def __init__(self, path: Path):
        self.path = path
        self.sessions: list[dict] = []
        if path.exists():
            if os.name == "posix" and path.stat().st_mode & 0o077:
                logger.warning("%s is readable by other users; run: chmod 600 %s", path, path)
            raw = yaml.safe_load(path.read_text()) or {}
            self.sessions = list(raw.get("sessions") or [])

    @staticmethod
    def _key(title_id: str, custom_id: str) -> tuple[str, str]:
        return str(title_id).upper(), str(custom_id)

    def get(self, title_id: str, custom_id: str) -> dict | None:
        k = self._key(title_id, custom_id)
        for s in self.sessions:
            if self._key(s["titleId"], s["customId"]) == k:
                return s
        return None

    def put(self, session: dict):
        k = self._key(session["titleId"], session["customId"])
        self.sessions = [s for s in self.sessions if self._key(s["titleId"], s["customId"]) != k]
        self.sessions.append(session)

    def mark_expired(self, title_id: str, custom_id: str):
        s = self.get(title_id, custom_id)
        if s:
            s["expired"] = True

    def remove(self, victims: list[dict]):
        ids = {id(v) for v in victims}
        self.sessions = [s for s in self.sessions if id(s) not in ids]

    def match(self, values=(), titles=(), expired_only=False) -> list[dict]:
        """Sessions matching any VALUE (custom ID, PlayFab ID, title alias or title ID,
        case-insensitive), within any of `titles` (alias or title ID), and expired if asked.
        Empty values/titles mean no restriction from that selector."""
        vals = {v.lower() for v in values}
        tits = {t.lower() for t in titles}
        out = []
        for s in self.sessions:
            fields = {str(s.get(k, "")).lower() for k in ("customId", "playFabId", "title", "titleId")}
            if vals and not vals & fields:
                continue
            if tits and not tits & {str(s.get("title", "")).lower(), str(s.get("titleId", "")).lower()}:
                continue
            if expired_only and not is_expired(s):
                continue
            out.append(s)
        return out

    def save(self):
        text = yaml.safe_dump({"sessions": self.sessions}, allow_unicode=True, sort_keys=False)
        tmp = self.path.with_name(self.path.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("# pfcli player sessions (gitignored, chmod 600). Tickets are credentials.\n")
            f.write(text)
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)
