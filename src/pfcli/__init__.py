"""pfcli: unofficial command-line tool for Microsoft PlayFab titles."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("playfab-cli-unofficial")
except PackageNotFoundError:  # running from a checkout without installing
    __version__ = "0.0.0+checkout"
