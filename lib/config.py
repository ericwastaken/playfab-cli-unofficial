"""Loads the YAML config (titles and hosts) and the YAML secrets file (secret keys by
title ID)."""
import copy
import logging
import os
import re
from pathlib import Path

import yaml

logger = logging.getLogger("pfcli")

ENV_PREFIX = "PFCLI_SECRET_"  # fallback: PFCLI_SECRET_<TITLE_ID> in the environment

RETIRED_KEYS = {
    "key_env": "keys come from the secrets file by title_id",
    "boards": "pass --statistic to server get-leaderboard",
    "default_name_patterns": "filter names with an output format's exclude",
}


CLOUDSCRIPT_KEYS = {"description", "writes", "parameter"}
PLAYER_ROLES = ("create", "update", "state")
SEQUENCE_KEYS = {"description", "steps"}
STEP_KEYS = {"cloudscript", "parameter", "call", "body", "description"}


class ConfigError(RuntimeError):
    pass


def _redact(raw, where: str) -> list[str]:
    """`redact`: regex patterns for title-specific credentials to hide in all output."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ConfigError(f"{where}: redact must be a list of regular expressions")
    for p in raw:
        try:
            re.compile(str(p))
        except re.error as e:
            raise ConfigError(f"{where}: bad redact pattern {p!r}: {e}")
    return [str(p) for p in raw]


def _player(raw, where: str) -> dict:
    """Normalize a `player` block: {create|update|state: {description, steps: [...]}}.
    Each step is {cloudscript: NAME, parameter: {...}} or {call: Family/Endpoint, body: {...}}."""
    from .client import ALLOWED_ENDPOINTS  # local import: client does not import config
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: player must be a map of {', '.join(PLAYER_ROLES)}")
    out = {}
    for role, seq in raw.items():
        if role not in PLAYER_ROLES:
            raise ConfigError(f"{where}: player.{role} is not a sequence pfcli knows; use {', '.join(PLAYER_ROLES)}")
        if seq is None:
            out[role] = None
            continue
        if not isinstance(seq, dict) or set(seq) - SEQUENCE_KEYS or not isinstance(seq.get("steps"), list):
            raise ConfigError(f"{where}: player.{role} must be a map with 'steps' (a list) and optional 'description'")
        steps = []
        for i, st in enumerate(seq["steps"], 1):
            label = f"{where}: player.{role} step {i}"
            if not isinstance(st, dict) or set(st) - STEP_KEYS:
                raise ConfigError(f"{label}: allowed keys are {', '.join(sorted(STEP_KEYS))}")
            if bool(st.get("cloudscript")) == bool(st.get("call")):
                raise ConfigError(f"{label}: needs exactly one of 'cloudscript' or 'call'")
            if st.get("call"):
                if st["call"] not in ALLOWED_ENDPOINTS:
                    raise ConfigError(f"{label}: endpoint {st['call']} is not registered in ALLOWED_ENDPOINTS")
                if "parameter" in st:
                    raise ConfigError(f"{label}: use 'body' with 'call' ('parameter' is for cloudscript)")
            if st.get("cloudscript") and "body" in st:
                raise ConfigError(f"{label}: use 'parameter' with 'cloudscript' ('body' is for call)")
            for k in ("parameter", "body"):
                if k in st and not isinstance(st[k], dict):
                    raise ConfigError(f"{label}: '{k}' must be a map")
            steps.append(dict(st))
        out[role] = {"description": str(seq.get("description") or ""), "steps": steps}
    return out


def _cloudscripts(raw, where: str) -> dict:
    """Normalize a `cloudscripts` block: a list of names, or a map of name -> null |
    {description, writes, parameter}. A null value in a title removes a default entry."""
    if raw is None:
        return {}
    if isinstance(raw, list):
        raw = {str(n): {} for n in raw}
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: cloudscripts must be a list of names or a map")
    out = {}
    for name, spec in raw.items():
        if spec is None:
            out[str(name)] = None
            continue
        if not isinstance(spec, dict):
            raise ConfigError(f"{where}: cloudscripts.{name} must be a map")
        unknown = set(spec) - CLOUDSCRIPT_KEYS
        if unknown:
            raise ConfigError(f"{where}: cloudscripts.{name} has unknown key(s) {', '.join(sorted(unknown))}; "
                              f"allowed: {', '.join(sorted(CLOUDSCRIPT_KEYS))}")
        param = spec.get("parameter") or {}
        if not isinstance(param, dict):
            raise ConfigError(f"{where}: cloudscripts.{name}.parameter must be a map")
        out[str(name)] = {"description": str(spec.get("description") or ""),
                          "writes": bool(spec.get("writes", True)), "parameter": param}
    return out


def paired_secrets_path(config_path: Path) -> Path | None:
    """pfcli-config[-<client>].yml -> pfcli-secrets[-<client>].yml in the same folder."""
    name = config_path.name
    if not name.startswith("pfcli-config"):
        return None
    return config_path.with_name("pfcli-secrets" + name[len("pfcli-config"):])


class Secrets:
    """Server API secret keys, keyed by title ID (case-insensitive)."""

    def __init__(self, path: Path | None):
        self.path = path
        self.keys: dict[str, str] = {}
        if path is None:
            return
        if not path.exists():
            raise ConfigError(f"Missing {path}. Copy pfcli-secrets.example.yml and fill in the keys.")
        if os.name == "posix" and path.stat().st_mode & 0o077:
            logger.warning("%s is readable by other users; run: chmod 600 %s", path, path)
        raw = yaml.safe_load(path.read_text()) or {}
        titles = raw.get("titles") or {}
        if not isinstance(titles, dict):
            raise ConfigError(f"{path}: 'titles' must be a map of title_id: key")
        for title_id, key in titles.items():
            key = "" if key is None else str(key).strip()
            if key:
                self.keys[str(title_id).upper()] = key

    def key_for(self, title_id: str) -> tuple[str, str]:
        """(key, source) where source is 'file', 'env' or '' when not found."""
        tid = title_id.upper()
        if tid in self.keys:
            return self.keys[tid], "file"
        env = os.environ.get(ENV_PREFIX + tid, "").strip()
        return (env, "env") if env else ("", "")


class Config:
    def __init__(self, path: Path, secrets: Secrets | None = None):
        if not path.exists():
            raise ConfigError(f"Missing {path}. Copy pfcli-config.example.yml to pfcli-config.yml and edit it.")
        raw = yaml.safe_load(path.read_text()) or {}
        self.path = path
        self.secrets = secrets or Secrets(None)
        self.defaults = raw.get("defaults") or {}
        for old, why in RETIRED_KEYS.items():
            if old in self.defaults:
                logger.warning("%s: defaults has '%s', which is no longer used; %s", path, old, why)
        self.default_cloudscripts = _cloudscripts(self.defaults.get("cloudscripts"), f"{path}: defaults")
        self.default_player = _player(self.defaults.get("player"), f"{path}: defaults")
        self.default_redact = _redact(self.defaults.get("redact"), f"{path}: defaults")
        self.titles = raw.get("titles") or {}
        if not self.titles:
            raise ConfigError(f"No titles defined in {path}. Add one with: pfcli init <name> --add-title ALIAS=TITLE_ID "
                              f"(or edit the file; see pfcli init --help)")
        for alias, t in self.titles.items():
            if not t.get("title_id"):
                raise ConfigError(f"{path}: title '{alias}' is missing 'title_id'")
            for old, why in RETIRED_KEYS.items():
                if old in t:
                    logger.warning("%s: title '%s' has '%s', which is no longer used; %s", path, alias, old, why)
            t["title_id"] = str(t["title_id"])  # YAML reads all-digit IDs as numbers
            t["cloudscripts"] = _cloudscripts(t.get("cloudscripts"), f"{path}: title '{alias}'")
            t["player"] = _player(t.get("player"), f"{path}: title '{alias}'")
            t["redact"] = _redact(t.get("redact"), f"{path}: title '{alias}'")

    def aliases(self) -> list[str]:
        return list(self.titles)

    def title(self, alias: str) -> dict:
        """Title settings with defaults applied (host formatted, cloudscripts merged by name)
        and its secret key resolved ('key', 'key_source')."""
        match = {a.lower(): a for a in self.titles}.get(alias.lower())
        if not match:
            raise ConfigError(f"Unknown title '{alias}'. Known: {', '.join(self.titles)}")
        t = copy.deepcopy(self.titles[match])
        t["alias"] = match
        t["host"] = (t.get("host") or self.defaults.get("host") or "https://{title_id}.playfabapi.com") \
            .format(title_id=t["title_id"]).rstrip("/")
        merged = {**copy.deepcopy(self.default_cloudscripts), **t["cloudscripts"]}
        t["cloudscripts"] = {n: s for n, s in merged.items() if s is not None}
        t["redact"] = self.default_redact + t["redact"]
        merged = {**copy.deepcopy(self.default_player), **t["player"]}
        t["player"] = {r: s for r, s in merged.items() if s is not None}
        t["key"], t["key_source"] = self.secrets.key_for(t["title_id"])
        return t
