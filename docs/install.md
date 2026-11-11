# Install pfcli

pfcli installs as a regular command with **uv**, straight from GitHub. uv takes care of
Python and pfcli's few dependencies in their own private environment, so nothing touches
your system Python.

!!! info "Want to work on pfcli's code?"
    This page is for **using** pfcli. To change pfcli itself, follow the **developer
    install** in the [README on GitHub](https://github.com/ericwastaken/playfab-cli-unofficial#developer-install).

## 1. Install uv

If you don't have uv yet, follow [uv's installation guide](https://docs.astral.sh/uv/getting-started/installation/)
(one command on macOS, Linux and Windows).

## 2. Install pfcli

Install a released version (recommended). Replace `v0.1.0` with the version you want from
the [Releases page](https://github.com/ericwastaken/playfab-cli-unofficial/releases):

```bash
uv tool install git+https://github.com/ericwastaken/playfab-cli-unofficial@v0.1.0
```

Check it:

```bash
pfcli --version
```

!!! tip "`pfcli: command not found`?"
    uv puts tools in its own folder. Run `uv tool update-shell` once, then open a new
    terminal.

??? note "Other ways to install"
    **Latest development version** (may change at any time):
    ```bash
    uv tool install git+https://github.com/ericwastaken/playfab-cli-unofficial
    ```
    **From a release's wheel file** (the `.whl` attached to each
    [release](https://github.com/ericwastaken/playfab-cli-unofficial/releases)):
    ```bash
    uv tool install https://github.com/ericwastaken/playfab-cli-unofficial/releases/download/v0.1.0/playfab_cli_unofficial-0.1.0-py3-none-any.whl
    ```
    **Run once without installing**:
    ```bash
    uvx --from git+https://github.com/ericwastaken/playfab-cli-unofficial@v0.1.0 pfcli --help
    ```

## 3. Make a pfcli folder

pfcli keeps **your** files (config, secrets, player logins, your own formats, exports) in a
folder you choose: your **pfcli home**. Make a private folder for them:

```bash
mkdir -p ~/pfcli
cd ~/pfcli
```

pfcli uses the folder you run it from. To use the same folder from anywhere, set
`PFCLI_HOME` (add it to `~/.zshrc` or `~/.bashrc` to keep it):

```bash
export PFCLI_HOME=~/pfcli
```

!!! warning "Keep this folder private"
    It will hold secret keys and player data. Don't put it inside a shared or synced folder
    you don't control, and don't commit it to Git. If you keep it in a Git repository, add
    these lines to that repository's `.gitignore`:
    ```gitignore
    pfcli*.yml
    pfcli*.yaml
    pfcli*.tmp
    output-formats/user-*
    request-templates/user-*
    pfcli-exports/
    ```

## Update or remove

```bash
uv tool install --force git+https://github.com/ericwastaken/playfab-cli-unofficial@v0.2.0   # update to a version
uv tool uninstall playfab-cli-unofficial                                                  # remove
```

Updating or removing pfcli never touches your pfcli folder.

Next: [Set up your titles](getting-started/setup.md).
