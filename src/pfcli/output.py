"""stdout output for every pfcli command.

Commands hand each result record to Emitter.emit(). A PlayFab call's record is an
envelope: {title, titleId, endpoint, at, request, [input], response} where `response` is
PlayFab's own reply, untouched. Without a format, each record is printed as one JSON line
(NDJSON); with --raw only `response` is printed. With --output-format, the same records
are reshaped by an output format file instead. Logs and progress never go to stdout.
"""
import csv
import json
import re
import sys
from pathlib import Path

import jmespath
import jmespath.functions
import yaml

from .files import NamedFileError, find_named

FORMATS = ("ndjson", "json", "yaml", "csv", "tsv", "text")
FORMAT_KEYS = {"format", "rows", "fields", "drop_empty", "exclude", "unique", "description"}
FORMATS_DIR = "output-formats"


class FormatError(RuntimeError):
    pass


def find_format(spec: str, config_dir: Path, home_dir: Path) -> Path:
    try:
        return find_named(spec, FORMATS_DIR, config_dir, home_dir, "Output format")
    except NamedFileError as e:
        raise FormatError(str(e))


class _Functions(jmespath.functions.Functions):
    """Extra JMESPath functions for output formats."""

    @jmespath.functions.signature({"types": ["object", "null"]})
    def _func_to_entries(self, obj):
        """{a: 1} -> [{key: "a", value: 1}] (like jq's to_entries)."""
        return [{"key": k, "value": v} for k, v in (obj or {}).items()]

    @jmespath.functions.signature({"types": ["string", "null"]})
    def _func_from_json(self, s):
        """Parse a JSON string (e.g. a UserData or TitleData value); non-JSON stays as is."""
        if s is None:
            return None
        try:
            return json.loads(s)
        except ValueError:
            return s


OPTIONS = jmespath.Options(custom_functions=_Functions())


class OutputFormat:
    def __init__(self, path: Path):
        self.path = path
        raw = yaml.safe_load(path.read_text()) or {}
        if not isinstance(raw, dict):
            raise FormatError(f"{path}: must be a YAML mapping")
        unknown = set(raw) - FORMAT_KEYS
        if unknown:
            raise FormatError(f"{path}: unknown key(s) {', '.join(sorted(unknown))}; "
                              f"allowed: {', '.join(sorted(FORMAT_KEYS))}")
        self.format = str(raw.get("format") or "ndjson").lower()
        if self.format not in FORMATS:
            raise FormatError(f"{path}: format must be one of {', '.join(FORMATS)}")
        try:
            self.rows = jmespath.compile(raw["rows"]) if raw.get("rows") else None
            self.fields = {str(k): jmespath.compile(str(v)) for k, v in (raw.get("fields") or {}).items()}
        except jmespath.exceptions.JMESPathError as e:
            raise FormatError(f"{path}: bad JMESPath expression: {e}")
        if self.format in ("csv", "tsv", "text") and not self.fields:
            raise FormatError(f"{path}: format '{self.format}' needs 'fields'")
        self.drop_empty = list(raw.get("drop_empty") or [])
        self.unique = list(raw.get("unique") or [])
        try:
            self.exclude = {f: [re.compile(p) for p in pats] for f, pats in (raw.get("exclude") or {}).items()}
        except re.error as e:
            raise FormatError(f"{path}: bad regex in 'exclude': {e}")
        for key in self.drop_empty + self.unique + list(self.exclude):
            if self.fields and key not in self.fields:
                raise FormatError(f"{path}: '{key}' is used in drop_empty/exclude/unique but is not a field")

    def shape(self, record):
        """Yield output rows for one record."""
        if self.rows is not None:
            items = self.rows.search(record, options=OPTIONS)
            items = [] if items is None else items if isinstance(items, list) else [items]
            contexts = [({**record, "row": it} if isinstance(record, dict) else {"row": it}, it) for it in items]
        else:
            contexts = [(record, record)]
        for ctx, item in contexts:
            row = {k: expr.search(ctx, options=OPTIONS) for k, expr in self.fields.items()} if self.fields else item
            if self.fields and not self._keep(row):
                continue
            yield row

    def _keep(self, row: dict) -> bool:
        if any(row.get(f) in (None, "", [], {}) for f in self.drop_empty):
            return False
        for f, pats in self.exclude.items():
            v = row.get(f)
            if v is not None and any(p.search(str(v)) for p in pats):
                return False
        return True


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


class Emitter:
    def __init__(self, fmt: OutputFormat | None = None, raw: bool = False, stream=None):
        self.fmt = fmt
        self.raw = raw
        self.out = stream or sys.stdout
        self.buffer = []
        self.seen = set()
        self.header_done = False
        self.writer = None
        if fmt and fmt.format in ("csv", "tsv"):
            self.writer = csv.writer(self.out, delimiter="," if fmt.format == "csv" else "\t", lineterminator="\n")

    def emit(self, record):
        if self.raw and isinstance(record, dict) and "response" in record:
            record = record["response"]
        if self.fmt is None:
            self._line(json.dumps(record, ensure_ascii=False))
            return
        for row in self.fmt.shape(record):
            if self.fmt.unique:
                key = json.dumps([row.get(f) for f in self.fmt.unique], ensure_ascii=False, sort_keys=True)
                if key in self.seen:
                    continue
                self.seen.add(key)
            self._row(row)

    def _row(self, row):
        f = self.fmt.format
        if f == "ndjson":
            self._line(json.dumps(row, ensure_ascii=False))
        elif f in ("json", "yaml"):
            self.buffer.append(row)
        elif f in ("csv", "tsv"):
            self._header()
            self.writer.writerow([_cell(row.get(k)) for k in self.fmt.fields])
            self.out.flush()
        else:  # text: values tab-separated, no header
            self._line("\t".join(_cell(row.get(k)) for k in self.fmt.fields))

    def _header(self):
        if not self.header_done:
            self.writer.writerow(list(self.fmt.fields))
            self.header_done = True

    def _line(self, s: str):
        self.out.write(s + "\n")
        self.out.flush()

    def finish(self):
        if self.fmt is None:
            return
        if self.fmt.format == "json":
            self.out.write(json.dumps(self.buffer, ensure_ascii=False, indent=2) + "\n")
        elif self.fmt.format == "yaml":
            self.out.write(yaml.safe_dump(self.buffer, allow_unicode=True, sort_keys=False))
        elif self.fmt.format in ("csv", "tsv"):
            self._header()  # header even when no rows matched
        self.out.flush()
