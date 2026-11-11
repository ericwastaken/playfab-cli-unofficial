"""Loads the YAML config (titles, hosts, boards, default-name patterns) and the YAML
secrets file (Server API secret keys by title ID)."""
import copy
import logging
import os
import re
from pathlib import Path

import yaml

logger = logging.getLogger("pfcli")

ENV_PREFIX = "PFCLI_SECRET_"  # fallback: PFCLI_SECRET_<TITLE_ID> in the environment


class ConfigError(RuntimeError):
    pass


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
        self.titles = raw.get("titles") or {}
        if not self.titles:
            raise ConfigError(f"No titles defined in {path}")
        for alias, t in self.titles.items():
            if not t.get("title_id"):
                raise ConfigError(f"{path}: title '{alias}' is missing 'title_id'")
            if "key_env" in t:
                logger.warning("%s: title '%s' has 'key_env', which is no longer used; "
                               "keys come from the secrets file by title_id", path, alias)
            t["title_id"] = str(t["title_id"])  # YAML reads all-digit IDs as numbers

    def aliases(self) -> list[str]:
        return list(self.titles)

    def title(self, alias: str) -> dict:
        """Title settings with defaults applied (host formatted, boards and patterns merged)
        and its secret key resolved ('key', 'key_source')."""
        match = {a.lower(): a for a in self.titles}.get(alias.lower())
        if not match:
            raise ConfigError(f"Unknown title '{alias}'. Known: {', '.join(self.titles)}")
        t = copy.deepcopy(self.titles[match])
        t["alias"] = match
        t["host"] = (t.get("host") or self.defaults.get("host") or "https://{title_id}.playfabapi.com") \
            .format(title_id=t["title_id"]).rstrip("/")
        t["boards"] = t.get("boards") or copy.deepcopy(self.defaults.get("boards") or {})
        t["default_name_patterns"] = [re.compile(p, re.IGNORECASE) for p in
                                      (t.get("default_name_patterns") or self.defaults.get("default_name_patterns") or [])]
        t["key"], t["key_source"] = self.secrets.key_for(t["title_id"])
        return t
