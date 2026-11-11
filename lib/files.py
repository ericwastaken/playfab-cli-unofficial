"""Finds named YAML files (output formats, request templates) the same way everywhere."""
from pathlib import Path


class NamedFileError(RuntimeError):
    pass


def find_named(spec: str, dirname: str, config_dir: Path, tool_dir: Path, label: str) -> Path:
    """A path (has a '/' or ends in .yml/.yaml) is used as given; a bare NAME is looked up as
    <dirname>/NAME.yml next to the config, then in the tool folder (built-in files)."""
    if "/" in spec or spec.endswith((".yml", ".yaml")):
        p = Path(spec).expanduser()
        if not p.exists():
            raise NamedFileError(f"{label} file not found: {spec}")
        return p
    tried = []
    for base in dict.fromkeys([config_dir.resolve(), tool_dir.resolve()]):
        p = base / dirname / f"{spec}.yml"
        tried.append(str(p))
        if p.exists():
            return p
    raise NamedFileError(f"{label} '{spec}' not found. Tried:\n  " + "\n  ".join(tried))
