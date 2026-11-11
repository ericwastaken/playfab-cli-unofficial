#!/usr/bin/env python3
"""Run pfcli from a source checkout without installing it: uv run pfcli.py --help
(Installed with `uv tool install`, the command is simply: pfcli)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from pfcli.cli import main  # noqa: E402

main()
