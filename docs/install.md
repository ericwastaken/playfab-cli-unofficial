# Install pfcli

pfcli runs from a folder on your computer. It uses **uv** to manage its own Python, so it
never touches your system Python.

## What you need

- **macOS, Linux or Windows** with a terminal.
- **Git**, to download pfcli.
- **uv**, the Python tool manager. If you don't have it, follow
  [uv's installation guide](https://docs.astral.sh/uv/getting-started/installation/)
  (one command on most systems).
- A **PlayFab title** you are allowed to work with, and its **title secret key** (for the
  `server` commands). Player commands don't need a secret key.

## Download and set up

```bash
git clone https://github.com/ericwastaken/playfab-cli-unofficial.git
cd playfab-cli-unofficial
uv sync
```

`uv sync` downloads the right Python and pfcli's few dependencies into a private `.venv`
folder inside `playfab-cli-unofficial`.

Check that it works:

```bash
uv run pfcli.py --help
```

You should see pfcli's commands and options.

## A shorter command

Throughout this guide, **`pfcli`** means `uv run pfcli.py`, run from the
`playfab-cli-unofficial` folder. To type `pfcli` from anywhere, add a shell alias (adjust the
path to where you cloned it):

```bash
alias pfcli='uv run --project ~/tools/playfab-cli-unofficial ~/tools/playfab-cli-unofficial/pfcli.py'
```

Put that line in your `~/.zshrc` or `~/.bashrc` to keep it.

## Update to the latest version

```bash
cd playfab-cli-unofficial
git pull
uv sync
```

Your own config, secrets and format files are never touched by an update: they're ignored by
Git (see [Files and Git](reference/files-and-git.md)).

!!! tip "Moved the folder?"
    The `.venv` folder doesn't survive being moved. If pfcli stops starting after a move,
    delete `.venv` and run `uv sync` again.

Next: [Set up your titles](getting-started/setup.md).
