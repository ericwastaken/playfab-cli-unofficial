"""Loads the YAML config: titles, hosts, key variable names, boards and default-name patterns."""
import copy
import re
from pathlib import Path

import yaml


class ConfigError(RuntimeError):
    pass


class Config:
    def __init__(self, path: Path):
        if not path.exists():
            raise ConfigError(f"Missing {path}. Copy pfcli.example.yml to pfcli.yml and edit it.")
        raw = yaml.safe_load(path.read_text()) or {}
        self.path = path
        self.defaults = raw.get("defaults") or {}
        self.titles = raw.get("titles") or {}
        if not self.titles:
            raise ConfigError(f"No titles defined in {path}")
        for alias, t in self.titles.items():
            for field in ("title_id", "key_env"):
                if not t.get(field):
                    raise ConfigError(f"{path}: title '{alias}' is missing '{field}'")
            t["title_id"] = str(t["title_id"])  # YAML reads all-digit IDs as numbers

    def aliases(self) -> list[str]:
        return list(self.titles)

    def title(self, alias: str) -> dict:
        """Title settings with defaults applied (host formatted, boards and patterns merged)."""
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
        return t
