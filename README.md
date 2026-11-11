# python-playfab-cli (`pfcli`)

A single **Click** CLI with subcommands for working with PlayFab titles.
Titles and hosts come from a YAML config and the secret keys from a YAML secrets file, so
the same tool works for any studio or game. It calls the PlayFab REST API directly (no
PlayFab SDK), so every request goes through one gate with an endpoint allow list. Runs through **uv** in
this folder's own `.venv` (Python 3.12, pinned in `.python-version`); the global Python is
never touched.

> This tool is not by Microsoft PlayFab, nor is it sanctioned by them.

## Layout

```
pfcli.py                    entry point (Click group, global options)
lib/config.py               loads and validates the YAML config and secrets
lib/client.py               Server API client with an endpoint allow list (ALLOWED_READS)
lib/commands/*.py           one module per command
pfcli-config.example.yml    config template   (committed)
pfcli-secrets.example.yml   secrets template  (committed)
output/                     default output folder (gitignored)
```

## Quick start

```bash
cp pfcli-config.example.yml  pfcli-config.yml    # 1. describe your titles
cp pfcli-secrets.example.yml pfcli-secrets.yml   # 2. paste each title's secret key
chmod 600 pfcli-secrets.yml
uv sync                                          # 3. create .venv (click, pyyaml)
uv run pfcli.py titles                           # 4. every title should show "key set"
```

## Config and secrets files

pfcli needs two YAML files: a **config** (what titles exist and how to reach them) and a
**secrets file** (the keys). They are linked by **title ID**: the secrets file maps each
`title_id` from the config to that title's Server API secret key.

| | Config | Secrets |
|---|---|---|
| Committed template | `pfcli-config.example.yml` | `pfcli-secrets.example.yml` |
| Default file (no flag) | `pfcli-config.yml` | `pfcli-secrets.yml` |
| Per-client file | `pfcli-config-<client>.yml` | `pfcli-secrets-<client>.yml` |
| Flag | `--config <path>` | `--secrets <path>` (usually not needed, see pairing) |
| Gitignored | yes, by pattern (below) | yes, by pattern (below) |
| Contains secrets? | **No.** Never put a key in the config. | **Yes.** `chmod 600`, never commit or paste. |

### Pairing

Without `--secrets`, pfcli looks next to the config for its partner, swapping
`pfcli-config` for `pfcli-secrets` in the file name:

| `--config` | Secrets file used |
|---|---|
| (default) `pfcli-config.yml` | `pfcli-secrets.yml` |
| `pfcli-config-acme.yml` | `pfcli-secrets-acme.yml` |
| `clients/pfcli-config-acme.yml` | `clients/pfcli-secrets-acme.yml` |
| any other name | none (environment only) unless `--secrets` is given |

If the paired file does not exist, keys come only from the environment (see the secrets
reference). An explicit `--secrets` that does not exist is an error. `uv run pfcli.py
titles` prints which config and secrets file it used.

### What git ignores (and keeps)

`.gitignore` ignores **every** config and secrets variant by pattern, then re-includes only
the two templates, so a new client file is safe without editing `.gitignore`:

```gitignore
pfcli*.yml
pfcli*.yaml
!pfcli-config.example.yml
!pfcli-secrets.example.yml
.env
.env.*
*.env
```

| File | In git? |
|---|---|
| `pfcli-config.example.yml`, `pfcli-secrets.example.yml` | **yes** (templates, no real values) |
| `pfcli-config.yml`, `pfcli-secrets.yml`, `pfcli-*-<client>.yml`, any other `pfcli*.yml` / `.yaml` | no |
| `.env`, `*.env` (pfcli does not use them; ignored so a stray one never leaks) | no |

The rule to follow: **every config and secrets file name starts with `pfcli` and ends in
`.yml`**, and it stays out of git automatically. Check a name with
`git check-ignore -v <file>`. Keep real title IDs, hosts and statistic names out of the
templates; they are committed.

### One pair per client

```bash
cp pfcli-config.example.yml  pfcli-config-acme.yml
cp pfcli-secrets.example.yml pfcli-secrets-acme.yml && chmod 600 pfcli-secrets-acme.yml
uv run pfcli.py --config pfcli-config-acme.yml titles     # pairs with pfcli-secrets-acme.yml
```

Resolution rules:

- **Defaults** (`pfcli-config.yml` and its pair) are looked up in **this tool's folder**,
  wherever you run the command from.
- **Explicit paths** are relative to your current directory, or absolute. A paired secrets
  file is looked up in the same folder as the config.
- A config that does not exist is always an error.

## YAML config reference

Full example (`pfcli-config.example.yml` with its comments removed):

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
    description: Example production title
  GAME-DEV:
    title_id: ABCD2
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
| `description` | no | string | Free text, shown by `titles`. |
| `host` | no | string | Overrides `defaults.host`. Needed for titles on a dedicated PlayFab cluster, whose API host is not the shared `playfabapi.com` one; the shared host answers `InvalidAPIEndpoint` for them. |
| `boards` | no | map | Overrides `defaults.boards` **entirely** (not merged): list every board the title should have. |
| `default_name_patterns` | no | list of regex | Overrides `defaults.default_name_patterns` **entirely**. |

A title missing `title_id`, or a config with no titles, fails on load with
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

A YAML file mapping title IDs to Server API secret keys. Template
(`pfcli-secrets.example.yml`):

```yaml
titles:
  ABCD1: ""
  ABCD2: ""
```

- **One entry per title** under `titles`: the key is the config's `title_id`, the value is
  that title's secret key. Title IDs match case-insensitively. Quote all-digit IDs.
- **Where the key comes from:** Game Manager > title > **Settings > Secret Keys** > **Show**
  on an active key. Prefer a dedicated key per tool or person so it can be revoked alone.
- **Format:** quote the key (`"..."`) so YAML keeps it as text. Empty values count as
  missing. One secrets file can hold keys for titles used by several configs.
- **Permissions:** `chmod 600` the file; pfcli warns on stderr when other users can read
  it. Never commit it, paste it into chat or tickets, or print it; `uv run pfcli.py titles`
  reports only `set (file)`, `set (env)` or `EMPTY`.
- **Environment fallback:** a title with no key in the file uses the environment variable
  `PFCLI_SECRET_<TITLE_ID>` (title ID upper-cased), e.g.
  `export PFCLI_SECRET_ABCD1=...`. Useful in CI. The file wins when both are set.
- A **missing** key makes that title show `key EMPTY` in `titles`; `leaderboard-names`
  skips the title with a message and exits with status 1.
- **Scope of the key:** a title secret key can call any Server and Admin API on that
  title, including writes. pfcli only sends the endpoints in `ALLOWED_READS`, but the key
  does not enforce that. Treat it as full access.

## Commands

Global options (before the command): `--config <yml>`, `--secrets <yml>`, `--json` (results
as JSON on stdout), `--log-level`. Run `uv run pfcli.py <command> --help` for details.

| Command | Calls PlayFab? | What it does |
|---|---|---|
| `titles` | no | Lists the config and secrets files used, then each title's ID, host, boards and whether its key is found (`set (file)`, `set (env)`, `EMPTY`). |
| `leaderboard-names ALIAS...` | yes, reads only | For each configured board, pulls the top `depth` ranks of the current statistic version with `Server/GetLeaderboard` (`ShowDisplayName`). Writes `<out>/<ALIAS>-<board>.json`. Options: `--board` to pick boards, `--depth BOARD=N` to override depth, `--out` (default `output/<YYMMDD>/`), `--pause`. 100 per page; retries on 429/5xx. |
| `names-report RAW_DIR` | no | From `leaderboard-names` output, writes `leaderboard-names.csv` (title, board, statistic, version, rank, display_name, default_name) and `known-good-names.csv` (unique names per title with boards, best_rank, default_name). Blanks are always removed. Names matching the title's `default_name_patterns` are flagged `default_name=yes` and dropped from known-good unless `--include-defaults` is passed. Uses `--config` for the patterns. Default output is the parent of `RAW_DIR`. |

Example:

```bash
uv run pfcli.py --config pfcli-config-acme.yml \
  leaderboard-names GAME-PROD GAME-DEV --out ~/work/names/raw
uv run pfcli.py --config pfcli-config-acme.yml names-report ~/work/names/raw
```

Notes:
- A board can return fewer rows than `depth` when fewer players have that statistic.
- "Known-good" means the name was accepted at the time it was set. A rule added later
  is not applied retroactively.

## Safety

Every PlayFab request goes through `PlayFabServer.call()` in `lib/client.py`, which only
sends endpoints listed in `ALLOWED_READS`; anything else raises before a request is made.
Today that list holds only read endpoints, so no current command changes anything on a
title. Any new endpoint has to be added to the list on purpose.

Things to weigh before adding a command that changes data or logs in as a player:

- A title secret key has full Server and Admin access, so a mistake in a write command
  hits live data directly.
- A Client API login (e.g. `LoginWithCustomID`) can create players or trigger the title's
  login CloudScript, which can write data, even when the command itself only reads.

## Adding a command

1. New module in `lib/commands/`, a `@click.command("name")` with `@click.pass_context`.
   `ctx.obj` holds `config` (a `Config`), `json_output` and `root`.
2. Call PlayFab through `PlayFabServer(config.title(alias)).call("<ReadApi>", body)`.
   Add each new endpoint to `ALLOWED_READS` (see Safety before adding one that writes).
3. Register it in `pfcli.py` (`cli.add_command(...)`) and add it to the table above.
4. If it needs new config keys, read them in `lib/config.py`, add them to
   `pfcli-config.example.yml`, and document them in the config reference above.
5. Dependencies: `uv add <package>`, never `pip install`.
