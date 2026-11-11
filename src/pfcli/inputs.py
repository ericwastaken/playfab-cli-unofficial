"""Input rows (CSV or NDJSON, from a file or stdin), request templates and placeholders.

Templates (request templates, CloudScript parameters, new-player steps) are YAML bodies.
A string value that is exactly one of these is replaced:

  $.<column>   the current input row's column
  $<name>      a variable: reserved ($session, $playFabId, $customId, $titleId, filled
               by pfcli) or given on the command line with --var <name>=<value>
  $<name>?     the same, but optional: when there is no value, the key (or list item)
               is left out instead of failing

Bodies are resolved before any call is made, so a missing value stops the run early.
"""
import copy
import csv
import io
import json
import re
import sys
from pathlib import Path

import yaml

from .files import NamedFileError, find_named

TEMPLATES_DIR = "request-templates"
COLUMN = re.compile(r"^\$\.(.+)$")
VARIABLE = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)(\?)?$")
RESERVED = ("session", "playFabId", "customId", "titleId")
_OMIT = object()


class InputError(RuntimeError):
    pass


def read_rows(source: str) -> list[dict]:
    """Rows from a file path or '-' (stdin). NDJSON when the first non-blank character is
    '{' (e.g. pfcli's own output), otherwise CSV with a header row."""
    text = sys.stdin.read() if source == "-" else Path(source).expanduser().read_text(encoding="utf-8-sig")
    stripped = text.lstrip()
    if not stripped:
        return []
    if stripped.startswith("{"):
        rows = []
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try:
                    obj = json.loads(line)
                except ValueError as e:
                    raise InputError(f"{source}: line {n} is not JSON: {e}")
                if not isinstance(obj, dict):
                    raise InputError(f"{source}: line {n} is not a JSON object")
                rows.append(obj)
        return rows
    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


def gather_rows(values: tuple[str, ...], column: str, source: str | None, from_column: str | None) -> list[dict]:
    """Rows from repeatable direct values (each becomes {column: value}) plus an --input
    source. from_column copies another column into `column` (e.g. playFabId -> PlayFabId)."""
    rows = [{column: v} for v in values]
    if source:
        for i, r in enumerate(read_rows(source), 1):
            r = dict(r)
            if from_column:
                if from_column not in r:
                    raise InputError(f"input row {i} has no column '{from_column}' "
                                     f"(columns: {', '.join(r)})")
                r[column] = r[from_column]
            rows.append(r)
    return rows


def load_template(spec: str | None, default: dict, config_dir: Path, home_dir: Path) -> dict:
    if not spec:
        return copy.deepcopy(default)
    try:
        path = find_named(spec, TEMPLATES_DIR, config_dir, home_dir, "Request template")
    except NamedFileError as e:
        raise InputError(str(e))
    body = yaml.safe_load(path.read_text()) or {}
    if not isinstance(body, dict):
        raise InputError(f"{path}: a request template must be a YAML mapping")
    return body


def parse_vars(pairs: tuple[str, ...]) -> dict:
    """--var NAME=VALUE pairs -> dict. Reserved names cannot be set."""
    out = {}
    for pair in pairs:
        k, sep, v = pair.partition("=")
        if not sep or not VARIABLE.match("$" + k) or k.endswith("?"):
            raise InputError(f"--var: expected NAME=VALUE with a simple NAME, got '{pair}'")
        if k in RESERVED:
            raise InputError(f"--var: '{k}' is filled by pfcli and cannot be set")
        out[k] = v
    return out


def resolve(template, row: dict | None = None, variables: dict | None = None, missing: list | None = None):
    """Copy of template with placeholders replaced. Unresolved required names are appended
    to `missing` (as '$.col' or '$name')."""
    row, variables = row or {}, variables or {}
    missing = [] if missing is None else missing

    def walk(v):
        if isinstance(v, dict):
            out = {}
            for k, x in v.items():
                r = walk(x)
                if r is not _OMIT:
                    out[k] = r
            return out
        if isinstance(v, list):
            return [r for r in (walk(x) for x in v) if r is not _OMIT]
        if isinstance(v, str):
            m = COLUMN.match(v)
            if m:
                val = row.get(m.group(1))
                if val in (None, ""):
                    missing.append(v)
                return val
            m = VARIABLE.match(v)
            if m:
                name, optional = m.group(1), bool(m.group(2))
                if variables.get(name) not in (None, ""):
                    return variables[name]
                if optional:
                    return _OMIT
                missing.append(f"${name}")
                return None
        return v

    return walk(template)


def placeholders(template) -> list[str]:
    """Variable placeholders in a template, e.g. ['$name?', '$session'] (sorted, unique)."""
    found = set()

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str) and (VARIABLE.match(v) or COLUMN.match(v)):
            found.add(v)
    walk(template)
    return sorted(found)


def build_bodies(template: dict, rows: list[dict], variables: dict | None = None) -> list[dict]:
    bodies = []
    for i, row in enumerate(rows, 1):
        missing = []
        bodies.append(resolve(template, row, variables, missing))
        if missing:
            raise InputError(f"input row {i}: no value for {', '.join(sorted(set(missing)))} "
                             f"(columns: {', '.join(row)}; set variables with --var NAME=VALUE)")
    return bodies
