# python-playfab-cli (`pfcli`)

A single **Click** CLI with subcommands for **read-only** work against PlayFab titles.
Titles, hosts and secret-key names come from a YAML config, and the keys themselves from
an env file, so the same tool works for any studio or game. Runs through **uv** in this
folder's own `.venv` (Python 3.12, pinned in `.python-version`); the global Python is
never touched.

> This tool is not by Microsoft PlayFab, nor is it sanctioned by them.

## Layout

```
pfcli.py              entry point (Click group, global options)
lib/config.py         loads and validates the YAML config
lib/client.py         read-only Server API client (ALLOWED_READS)
lib/commands/*.py     one module per command
pfcli.example.yml     config template   (committed)
.env.example          secrets template  (committed)
output/               default output folder (gitignored)
```

## Quick start

```bash
cp pfcli.example.yml pfcli.yml     # 1. describe your titles
cp .env.example .env               # 2. paste each title's secret key
chmod 600 .env
uv sync                            # 3. create .venv (click, python-dotenv, pyyaml)
uv run pfcli.py titles             # 4. check: every title should show "key set"
```

## Config and secrets files

pfcli needs two files: a **YAML config** (what titles exist and how to reach them) and a
**secrets file** (the keys). They are linked by variable name: each title in the config
names the env variable (`key_env`) that holds its key in the secrets file.

| | Config | Secrets |
|---|---|---|
| Committed template | `pfcli.example.yml` | `.env.example` |
| Default file (no flag) | `pfcli.yml` | `.env` |
| Per-client file | `pfcli-config-<client>.yml` | `pfcli-secrets-<client>.env` |
| Flag | `--config <path>` | `--env <path>` |
| Gitignored | every `pfcli*.yml` / `pfcli*.yaml` except the example | every `.env`, `.env.*`, `*.env` except the example |
| Contains secrets? | **No.** Never put a key in YAML. | **Yes.** `chmod 600`, never commit or paste. |

### What git ignores (and keeps)

`.gitignore` ignores **every** config and secrets variant by pattern, then re-includes only
the two templates, so a new client file is safe without editing `.gitignore`:

```gitignore
pfcli*.yml
pfcli*.yaml
!pfcli.example.yml
.env
.env.*
*.env
!.env.example
```

| File | In git? |
|---|---|
| `pfcli.example.yml`, `.env.example` | **yes** (templates, no real values) |
| `pfcli.yml`, `pfcli-config-<client>.yml`, any other `pfcli*.yml` / `.yaml` | no |
| `.env`, `.env.local`, `pfcli-secrets-<client>.env`, any other `*.env` | no |

The rule to follow: **name config files `pfcli…yml` and secrets files `…env`**, and they
stay out of git automatically. Check a name with `git check-ignore -v <file>`. Keep real
title IDs, hosts and statistic names out of the templates; they are committed.

### One pair per client

To keep clients apart, give each its own pair and pass both explicitly:

```bash
cp pfcli.example.yml pfcli-config-acme.yml
cp .env.example      pfcli-secrets-acme.env && chmod 600 pfcli-secrets-acme.env
uv run pfcli.py --config pfcli-config-acme.yml --env pfcli-secrets-acme.env titles
```

Resolution rules:

- **Defaults** (`pfcli.yml`, `.env`) are looked up in **this tool's folder**, wherever you
  run the command from.
- **Explicit paths** are relative to your current directory, or absolute.
- A config that does not exist is always an error. An explicit `--env` that does not exist
  is an error; a missing default `.env` is allowed (keys then come only from your shell
  environment, see below).

## YAML config reference

Full example (`pfcli.example.yml` with its comments removed):

```yaml
defaults:
  host: "https://{title_id}.playfabapi.com"
  boards:
    alltime: { statistic: score, depth: 5000 }
    today:   { statistic: score_daily, depth: 500 }
  default_name_patterns:
    - '^player_?\d{5,}$'

titles:
  GAME-PROD:
    title_id: ABCD1
    key_env: SERVER_SECRET_KEY_ABCD1
    description: Example production title
  GAME-DEV:
    title_id: ABCD2
    key_env: SERVER_SECRET_KEY_ABCD2
    description: Example dev title on a dedicated cluster
    host: "https://{title_id}.example-cluster.playfabapi.com"
    default_name_patterns: ['^guest\d{5,}$']
```

### `defaults` (optional)

Values every title inherits unless the title sets its own.

| Key | Type | Used by | Meaning |
|---|---|---|---|
| `host` | string | all API calls | Server API base URL. `{title_id}` is replaced with the title's ID; a trailing `/` is dropped. If unset anywhere, `https://{title_id}.playfabapi.com`. |
| `boards` | map | `leaderboard-names` | Board label to `{ statistic, depth }`. See below. |
| `default_name_patterns` | list of regex | `names-report` | Display names matching any pattern are treated as auto-assigned defaults. |

### `titles` (required, at least one)

Each key under `titles` is an **alias**: the short name you type on the command line and
the label used in output file names and CSV rows. Aliases are matched case-insensitively
(`game-prod` finds `GAME-PROD`); output uses the spelling in the config.

| Key | Required | Type | Meaning |
|---|---|---|---|
| `title_id` | **yes** | string | The PlayFab title ID (Game Manager > title > Settings > General). **Quote it** if it is all digits (`"12345"`); pfcli also coerces it to text. |
| `key_env` | **yes** | string | Name of the variable in the secrets file that holds this title's Server API secret key, e.g. `SERVER_SECRET_KEY_ABCD1`. |
| `description` | no | string | Free text, shown by `titles`. |
| `host` | no | string | Overrides `defaults.host`. Needed for titles on a dedicated PlayFab cluster, whose API host is not the shared `playfabapi.com` one; the shared host answers `InvalidAPIEndpoint` for them. |
| `boards` | no | map | Overrides `defaults.boards` **entirely** (not merged): list every board the title should have. |
| `default_name_patterns` | no | list of regex | Overrides `defaults.default_name_patterns` **entirely**. |

A title missing `title_id` or `key_env`, or a config with no titles, fails on load with
the file and alias named.

### `boards`

```yaml
boards:
  <label>: { statistic: <PlayFab statistic name>, depth: <ranks to pull> }
```

- `<label>` is yours to choose (`alltime`, `today`, `weekly`, ...). It names the output
  file (`<ALIAS>-<label>.json`) and is what `--board` and `--depth` refer to.
- `statistic` is the legacy leaderboard / statistic name exactly as in Game Manager
  (Leaderboards (Legacy)). Case-sensitive.
- `depth` is how many top ranks to pull; omitted means 100. Override per run with
  `--depth <label>=N`.
- The **current version** of the statistic is always read, so a daily or hourly statistic
  gives the current day's or hour's board.

### `default_name_patterns`

- Python regular expressions, matched **case-insensitively** anywhere in the name
  (`re.search`); anchor with `^...$` to match whole names.
- Use single quotes in YAML so backslashes survive: `'^player_?\d{5,}$'`.
- Each title has its own default-name format (separator, language, digit count). Check a
  sample of `leaderboard-names.csv` and set patterns per title, or defaults will be counted
  as known-good.

## Secrets file reference

A plain `KEY=value` file read with python-dotenv. Template (`.env.example`):

```bash
# PlayFab Server API secret keys. Copy to .env, or to pfcli-secrets-<client>.env
# (both gitignored), chmod 600, and fill in.
# Game Manager > <title> > Settings > Secret Keys > Show.
# Variable names must match each title's key_env in the config.
SERVER_SECRET_KEY_ABCD1=
SERVER_SECRET_KEY_ABCD2=
```

- **One line per title**, the variable name equal to that title's `key_env`. Variable names
  are your choice; `SERVER_SECRET_KEY_<TITLEID>` keeps them unambiguous.
- **Where the key comes from:** Game Manager > title > **Settings > Secret Keys** > **Show**
  on an active key. Prefer a dedicated key per tool or person so it can be revoked alone.
- **Format:** the key as-is after `=`. Quotes are optional and stripped. Lines starting with
  `#` are comments. No spaces around `=`.
- **Permissions:** `chmod 600` the file. Never commit it, paste it into chat or tickets, or
  print it; `uv run pfcli.py titles` reports only `set` / `EMPTY`.
- **Precedence:** values in the secrets file override variables of the same name already
  set in your shell. If no secrets file is loaded (default `.env` absent), pfcli uses
  whatever is in the shell environment, so `export SERVER_SECRET_KEY_ABCD1=...` also works.
- An **empty or missing** variable makes that title show `key EMPTY` in `titles`;
  `leaderboard-names` skips the title with a message and exits with status 1.
- **Scope of the key:** a title secret key can call any Server and Admin API on that
  title, including writes. pfcli itself only sends the read endpoints in `ALLOWED_READS`,
  but the key does not enforce that. Treat it as full access.

## Commands

Global options (before the command): `--config <yml>`, `--env <file>`, `--json` (results
as JSON on stdout), `--log-level`. Run `uv run pfcli.py <command> --help` for details.

| Command | Calls PlayFab? | What it does |
|---|---|---|
| `titles` | no | Lists configured titles, hosts, boards and whether each key is set. |
| `leaderboard-names ALIAS...` | read-only | For each configured board, pulls the top `depth` ranks of the current statistic version with `Server/GetLeaderboard` (`ShowDisplayName`). Writes `<out>/<ALIAS>-<board>.json`. Options: `--board` to pick boards, `--depth BOARD=N` to override depth, `--out` (default `output/<YYMMDD>/`), `--pause`. 100 per page; retries on 429/5xx. |
| `names-report RAW_DIR` | no | From `leaderboard-names` output, writes `leaderboard-names.csv` (title, board, statistic, version, rank, display_name, default_name) and `known-good-names.csv` (unique names per title with boards, best_rank, default_name). Blanks are always removed. Names matching the title's `default_name_patterns` are flagged `default_name=yes` and dropped from known-good unless `--include-defaults` is passed. Uses `--config` for the patterns. Default output is the parent of `RAW_DIR`. |

Example:

```bash
uv run pfcli.py --config pfcli-config-acme.yml --env pfcli-secrets-acme.env \
  leaderboard-names GAME-PROD GAME-DEV --out ~/work/names/raw
uv run pfcli.py --config pfcli-config-acme.yml names-report ~/work/names/raw
```

Notes:
- A board can return fewer rows than `depth` when fewer players have that statistic.
- "Known-good" means the name was accepted at the time it was set. A rule added later
  is not applied retroactively.

## Safety

`lib/client.py` only sends endpoints listed in `ALLOWED_READS`; anything else raises before
a request is made. Use the Server API with a secret key, never the Client API, for data
pulls: a client login can create players or trigger login CloudScript that writes data.

## Adding a command

1. New module in `lib/commands/`, a `@click.command("name")` with `@click.pass_context`.
   `ctx.obj` holds `config` (a `Config`), `json_output` and `root`.
2. Call PlayFab through `PlayFabServer(config.title(alias)).call("<ReadApi>", body)`.
   Add new read endpoints to `ALLOWED_READS`; never add a write endpoint.
3. Register it in `pfcli.py` (`cli.add_command(...)`) and add it to the table above.
4. If it needs new config keys, read them in `lib/config.py`, add them to
   `pfcli.example.yml`, and document them in the config reference above.
5. Dependencies: `uv add <package>`, never `pip install`.
