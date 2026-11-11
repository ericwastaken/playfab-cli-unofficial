"""Where pfcli looks for files.

- Your files (config, secrets, sessions, user-* formats and templates, exports) live in
  your pfcli "home": the folder named by the PFCLI_HOME environment variable, or else the
  folder you run pfcli from.
- Built-in output formats and request templates ship inside the package (pfcli/builtin).
"""
import os
from importlib.resources import files
from pathlib import Path

BUILTIN = Path(str(files("pfcli") / "builtin"))


class NamedFileError(RuntimeError):
    pass


def home() -> Path:
    """The folder for the user's pfcli files: $PFCLI_HOME, or the current folder."""
    h = os.environ.get("PFCLI_HOME")
    return Path(h).expanduser() if h else Path.cwd()


def find_named(spec: str, dirname: str, config_dir: Path, home_dir: Path, label: str) -> Path:
    """A path (has a '/' or ends in .yml/.yaml) is used as given; a bare NAME is looked up as
    <dirname>/NAME.yml next to the config, then in the pfcli home folder, then among the
    built-in files that ship with pfcli."""
    if "/" in spec or spec.endswith((".yml", ".yaml")):
        p = Path(spec).expanduser()
        if not p.exists():
            raise NamedFileError(f"{label} file not found: {spec}")
        return p
    tried = []
    for base in dict.fromkeys([config_dir.resolve() / dirname, home_dir.resolve() / dirname, BUILTIN / dirname]):
        p = base / f"{spec}.yml"
        tried.append(str(p))
        if p.exists():
            return p
    raise NamedFileError(f"{label} '{spec}' not found. Tried:\n  " + "\n  ".join(tried))
