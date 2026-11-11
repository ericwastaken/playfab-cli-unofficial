# python-playfab-cli (`pfcli`)

A single **Click** CLI with subcommands for working with PlayFab titles.
Titles and hosts come from a YAML config and the secret keys from a YAML secrets file, so
the same tool works for any studio or game. It calls the PlayFab REST API directly (no
PlayFab SDK), so every request goes through one gate and every command is tagged
`READ ONLY` or `READ WRITE`. Output is PlayFab's own JSON on stdout by default, and any
command's output can be reshaped with an output format file. Runs through **uv** in
this folder's own `.venv` (Python 3.12, pinned in `.python-version`); the global Python is
never touched.

> This tool is not by Microsoft PlayFab, nor is it sanctioned by them.

## Layout

```
pfcli.py                    entry point (Click group, global options)
lib/config.py               loads and validates the YAML config and secrets
lib/client.py               secret-key client (Server/Admin) + ALLOWED_ENDPOINTS registry
lib/pfcommand.py            pf_command: access tag, endpoint check, --dry-run
lib/output.py               stdout output: envelopes, --raw, output formats
lib/commands/*.py           top-level commands (titles)
lib/commands/server/*.py    `server` group commands, one module per command
pfcli-config.example.yml    config template   (committed)
pfcli-secrets.example.yml   secrets template  (committed)
output-formats/             your output formats (gitignored) + committed *.example.yml
```

## Quick start

```bash
cp pfcli-config.example.yml  pfcli-config.yml    # 1. describe your titles
cp pfcli-secrets.example.yml pfcli-secrets.yml   # 2. paste each title's secret key
chmod 600 pfcli-secrets.yml
uv sync                                          # 3. create .venv (click, jmespath, pyyaml)
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

titles:
  GAME-PROD:
    title_id: ABCD1
    description: Example production title
  GAME-DEV:
    title_id: ABCD2
    description: Example dev title on a dedicated cluster
    host: "https://{title_id}.example-cluster.playfabapi.com"
```

The config only says which titles exist and how to reach them. What to read (statistic
names, keys) is given on the command line, and how to shape the output is an output
format (see Output).

### `defaults` (optional)

| Key | Type | Meaning |
|---|---|---|
| `host` | string | API base URL. `{title_id}` is replaced with the title's ID; a trailing `/` is dropped. If unset anywhere, `https://{title_id}.playfabapi.com`. |

### `titles` (required, at least one)

Each key under `titles` is an **alias**: the short name you type on the command line and
the `title` value in output. Aliases are matched case-insensitively (`game-prod` finds
`GAME-PROD`); output uses the spelling in the config.

| Key | Required | Type | Meaning |
|---|---|---|---|
| `title_id` | **yes** | string | The PlayFab title ID (Game Manager > title > Settings > General). **Quote it** if it is all digits (`"12345"`); pfcli also coerces it to text. |
| `description` | no | string | Free text, shown by `titles`. |
| `host` | no | string | Overrides `defaults.host`. Needed for titles on a dedicated PlayFab cluster, whose API host is not the shared `playfabapi.com` one; the shared host answers `InvalidAPIEndpoint` for them. |

A title missing `title_id`, or a config with no titles, fails on load with the file and
alias named. Retired keys (`key_env`, `boards`, `default_name_patterns`) are ignored with a
warning on stderr.

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
- A **missing** key makes that title show `key EMPTY` in `titles`; commands that call
  PlayFab skip the title with a message on stderr and exit with status 1.
- **Scope of the key:** a title secret key can call any Server and Admin API on that
  title, including writes. pfcli only calls endpoints registered in `ALLOWED_ENDPOINTS`, but
  the key itself does not limit anything. Treat it as full access.

## Several titles in one command

Commands that call PlayFab take **one or more title aliases**, so one run can cover a whole
set of titles, for example every region of a game or prod and dev side by side:

```bash
uv run pfcli.py --config pfcli-config-acme.yml -o leaderboard-names \
  server get-leaderboard GAME-PROD GAME-DEV GAME-ASIA -s score --max 5000 > names.csv
```

- **Each title is called with its own settings**: its own host (shared or dedicated
  cluster) and its own secret key from the secrets file. Mixing titles on different
  clusters in one run just works.
- **Titles run in the order given**, one after the other, and their results go to the
  same stdout stream.
- **Every record says which title it came from**: the envelope's `title` (the alias) and
  `titleId`. Output formats and `jq` can use those to label, filter or split results;
  the example names format puts `title` in the first column and de-duplicates names
  per title (`unique: [title, name]`).
- **One title failing does not stop the others**: an unknown alias, a missing key or a
  PlayFab error is reported on stderr, that title is skipped, the rest still run, and
  the exit status is 1 so scripts can tell.
- Aliases are matched case-insensitively; `uv run pfcli.py --config ... titles` lists them.

Split a combined run afterwards, e.g. one file per title:

```bash
uv run pfcli.py --config pfcli-config-acme.yml -o leaderboard-entries \
  server get-leaderboard GAME-PROD GAME-DEV -s score --max 1000 \
  | jq -c 'select(.title == "GAME-DEV")' > dev.ndjson
```

## Output

pfcli writes **data to stdout** and everything else (logs, progress, warnings, errors,
dry-run notices) to **stderr**, so output can be piped or redirected with plain shell:

```bash
uv run pfcli.py ... server get-leaderboard GAME-PROD -s score > board.ndjson
uv run pfcli.py ... server get-leaderboard GAME-PROD -s score 2> errors.log | jq .
```

### Default: PlayFab's own responses, one JSON line per call

Each PlayFab call prints one line (NDJSON) holding PlayFab's response untouched, inside a
small envelope saying which title and request it belongs to:

```json
{"title": "GAME-PROD", "titleId": "ABCD1", "endpoint": "Server/GetLeaderboard",
 "request": {"StatisticName": "score", "StartPosition": 0, ...},
 "response": {"code": 200, "status": "OK", "data": {"Leaderboard": [...], "Version": 3}}}
```

- A command that makes several calls (pages, several titles) prints several lines.
- PlayFab errors are printed the same way (`response` is PlayFab's error reply); a message
  also goes to stderr and the exit status is 1.
- A write sent with `--dry-run` prints its envelope with `"dryRun": true` and
  `"response": null`.
- `--raw` prints only `response`, exactly as PlayFab returned it.
- Commands that make no PlayFab call (`titles`) print one JSON line per record.

### `--output-format`: reshape any command's output

`--output-format NAME|PATH` (`-o`, a global option, before the command) passes every
record through an **output format file** instead. It works with every command; formats
are not tied to one. A bare `NAME` is looked up as `output-formats/NAME.yml`, then
`output-formats/NAME.example.yml`, next to the config file and then in this tool's folder;
anything with a `/` or ending in `.yml` is used as a path.

`output-formats/` holds your formats and is **gitignored**, except the committed generic
`*.example.yml` ones. Copy an example to `NAME.yml` to customize it.

```yaml
# output-formats/leaderboard-names.yml
description: Unique display names per title
format: csv                        # ndjson (default) | json | yaml | csv | tsv | text
rows: response.data.Leaderboard    # optional: one output row per item of this list
fields:                            # optional: output columns (needed for csv/tsv/text)
  title: title                     #   envelope values by name
  position: row.Position           #   `row` is the current item from `rows`
  name: row.DisplayName
drop_empty: [name]                 # optional: drop rows where these fields are empty
exclude:                           # optional: drop rows where a field matches a regex
  name: ['^player_?\d{5,}$']
unique: [title, name]              # optional: keep only the first row per combination
```

| Key | Meaning |
|---|---|
| `format` | `ndjson` one JSON object per line (default); `json` / `yaml` one list, written at the end; `csv` / `tsv` with a header row; `text` tab-separated values, no header. |
| `rows` | [JMESPath](https://jmespath.org/) expression evaluated on each record. A list gives one output row per item, a single value one row, null none. Omit it for one row per record. |
| `fields` | Output name to JMESPath expression. Evaluated on the record plus `row` (the current item). Without `fields`, the item itself (or the record) is printed. Lists and objects in csv/tsv/text cells are written as JSON. |
| `drop_empty` | Fields that must not be empty (null, `""`, `[]`, `{}`). |
| `exclude` | Field to list of Python regexes (`re.search`, case-sensitive; add `(?i)` to ignore case). A match drops the row. Use single quotes in YAML so backslashes survive. |
| `unique` | Fields whose combination may appear only once; the first row wins. |
| `description` | Free text. |

The format applies to whatever would otherwise be printed: with `--raw`, expressions see
PlayFab's response instead of the envelope. Unknown keys, bad expressions and bad regexes
are reported before any call is made.

Committed examples:

| Name | What it prints |
|---|---|
| `leaderboard-names` | CSV of unique display names per title from `server get-leaderboard`, with blanks and default-looking names removed. |
| `leaderboard-entries` | One JSON line per leaderboard entry (title, statistic, position, playFabId, name, value). |
| `data` | Only the `data` of each PlayFab response. |
| `titles-table` | `titles` as TSV. |

## Commands

Global options (before the command): `--config`, `--secrets`, `--output-format`/`-o`,
`--raw`, `--log-level`. `ALIAS...` means one or more title aliases. Commands that call PlayFab are grouped by PlayFab API family
(`server ...`; `admin` and `client` groups will follow) and named after the endpoint they
call. Run `uv run pfcli.py <command> --help` for details.

| Command | Access (PlayFab endpoints) | What it does |
|---|---|---|
| `titles` | READ ONLY (none) | One record per configured title: alias, titleId, host, key (`set (file)`, `set (env)`, `EMPTY`) and description. The config and secrets files used are reported on stderr. |
| `server get-leaderboard ALIAS... -s STAT` | READ ONLY (`Server/GetLeaderboard`) | Reads a legacy leaderboard (statistic) for **each title given** (see Several titles in one command), paging 100 at a time, with display names. One record per page. Options: `--max N` ranks per title (default 100), `--start N`, `--version N` (default: current), `--pause`. Warns on stderr when a board is empty (PlayFab returns an empty board for a statistic that does not exist). |

Examples:

```bash
# Raw pages, for jq or later processing
uv run pfcli.py --config pfcli-config-acme.yml \
  server get-leaderboard GAME-PROD GAME-DEV -s score --max 5000 > score.ndjson

# Names list as CSV
uv run pfcli.py --config pfcli-config-acme.yml -o leaderboard-names \
  server get-leaderboard GAME-PROD GAME-DEV -s score --max 5000 > names.csv
```

Notes:
- A board can return fewer rows than `--max` when fewer players have that statistic.
- The current version of a statistic is read unless `--version` is given, so a daily or
  hourly statistic gives the current day's or hour's board.

## Access and safety

pfcli is **not** read-only by design. What a command can do on a title is decided by the
credentials you give it (a title secret key has full Server and Admin access); pfcli's
job is to make each command's effect obvious:

- **Every command is tagged** `READ ONLY` or `READ WRITE`, shown in `pfcli --help` and at
  the top of the command's own `--help`, together with the PlayFab endpoints it calls.
- **Endpoints are named by API family**, as in PlayFab's REST API: `Server/...`,
  `Admin/...`, `Client/...`. Each is registered in `ALLOWED_ENDPOINTS` (`lib/client.py`)
  as `read` or `write`; an unregistered endpoint raises before any request is sent.
- **Every `READ WRITE` command has `--dry-run`**: write requests are printed, not sent;
  reads still run so the output shows what would change.
- Declarations are checked when pfcli starts: a `READ ONLY` command that lists a write
  endpoint, or a `READ WRITE` command with none, fails immediately.

Things to keep in mind:

- A title secret key reaches live data directly; try a write with `--dry-run` first.
- `Client/...` endpoints need a player session, not the secret key. A Client login (e.g.
  `LoginWithCustomID`) can create players or trigger the title's login CloudScript,
  which can write data, even when the command itself only reads. `TitleClient` does not
  support the Client API yet.

## Adding a command

1. New module in `lib/commands/`. Declare it with `pf_command` (`lib/pfcommand.py`)
   instead of `click.command`, naming its access and every endpoint it calls:
   ```python
   @pf_command("my-command", READ_ONLY, ("Server/GetTitleData",))
   @click.pass_context
   def my_command(ctx, ...):
       """One-line summary."""
   ```
   A `READ_WRITE` command gets a `dry_run` argument (from `--dry-run`); pass it to every
   `call(...)`. `ctx.obj` is the app: `ctx.obj.config` (a `Config`, loaded on first use),
   `ctx.obj.emitter`, `ctx.obj.root`. Commands calling an API family go in that family's
   group (`server`, later `admin` / `client`), named after the endpoint in kebab-case.
2. Register each new endpoint in `ALLOWED_ENDPOINTS` with its family and `READ`/`WRITE`.
3. Call PlayFab through `TitleClient(config.title(alias)).call("Server/<Name>", body,
   dry_run=dry_run)`. It returns the envelope with PlayFab's reply (errors included);
   pass it to `ctx.obj.emitter.emit(...)`, check it with `ok(env)`, and write any
   message to stderr. Never print data any other way: formats only see emitted records.
4. Register the command in `pfcli.py` (`cli.add_command(...)` or
   `server.add_command(...)`) and add it to the Commands table above.
5. If it needs new config keys, read them in `lib/config.py`, add them to
   `pfcli-config.example.yml`, and document them in the config reference above.
6. Dependencies: `uv add <package>`, never `pip install`.
