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
lib/inputs.py               input rows (CSV/NDJSON) and request templates
lib/sessions.py             saved player sessions for client commands
lib/commands/*.py           top-level commands (titles) and shared helpers
lib/commands/server/*.py    `server` group commands, one module per command
lib/commands/client/*.py    `client` group commands and `client sessions`
pfcli-config.example.yml    config template   (committed)
pfcli-secrets.example.yml   secrets template  (committed)
output-formats/             built-in output formats (committed) + your user-*.yml (gitignored)
request-templates/          built-in request templates (committed) + your user-*.yml (gitignored)
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
| `pfcli-sessions[-<client>].yml` (player session tickets), `pfcli*.tmp` | no |
| `output-formats/user-*`, `request-templates/user-*` (your own) | no |
| Other files in `output-formats/`, `request-templates/` (built-in, generic) | **yes** |
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
    cloudscripts:
      getPlayerState:
        description: Read the player's saved state
        writes: false
        parameter: { session: $session }
      savePlayerSettings:
        description: Save the player's settings
        parameter: { id: $playFabId, session: $session, name: "$name?", color: "$color?" }
    player:
      create:                                   # endpoint calls
        steps:
          - call: Server/UpdateUserData
            body: { PlayFabId: $playFabId, Data: { profileVersion: "1", color: "$color?" } }
          - call: Client/UpdateUserTitleDisplayName
            body: { DisplayName: $name }
      update:                                   # CloudScript
        steps:
          - cloudscript: savePlayerSettings
      state:                                    # endpoint calls, reads only
        steps:
          - call: Client/GetPlayerProfile
            body: { PlayFabId: $playFabId, ProfileConstraints: { ShowDisplayName: true } }
          - call: Client/GetUserData
            body: { Keys: [profileVersion, color] }
    redact:
      - 'LOGINKEY-[0-9a-f]+'
```

The config says which titles exist, how to reach them, which CloudScript functions
players may run through pfcli, and how the title creates, updates and reads its players.

> **Title-specific parts stay in your own config.** CloudScript names, parameter shapes
> and player sequences are unique to a game. Put them only in your gitignored
> `pfcli-config-<client>.yml`; the committed `pfcli-config.example.yml` and this README
> use generic names (`savePlayerSettings`, `getPlayerState`) as examples. What to read (statistic
names, keys) is given on the command line, and how to shape the output is an output
format (see Output).

### `defaults` (optional)

| Key | Type | Meaning |
|---|---|---|
| `host` | string | API base URL. `{title_id}` is replaced with the title's ID; a trailing `/` is dropped. If unset anywhere, `https://{title_id}.playfabapi.com`. |
| `cloudscripts` | map or list | CloudScript functions allowed on every title (see below). |
| `player` | map | Player sequences shared by every title (see below). |

### `titles` (required, at least one)

Each key under `titles` is an **alias**: the short name you type on the command line and
the `title` value in output. Aliases are matched case-insensitively (`game-prod` finds
`GAME-PROD`); output uses the spelling in the config.

| Key | Required | Type | Meaning |
|---|---|---|---|
| `title_id` | **yes** | string | The PlayFab title ID (Game Manager > title > Settings > General). **Quote it** if it is all digits (`"12345"`); pfcli also coerces it to text. |
| `description` | no | string | Free text, shown by `titles`. |
| `host` | no | string | Overrides `defaults.host`. Needed for titles on a dedicated PlayFab cluster, whose API host is not the shared `playfabapi.com` one; the shared host answers `InvalidAPIEndpoint` for them. |
| `cloudscripts` | no | map or list | CloudScript functions `client execute-cloud-script` may run on this title. Merged with `defaults.cloudscripts` by name; `name: null` removes a default. |
| `player` | no | map | How the title creates, updates and reads players (`create`, `update`, `state`). Each overrides the same one in `defaults.player`; `create: null` removes a default. |
| `redact` | no | list of regex | Title-specific credentials (e.g. a login key the game's data or CloudScript returns) replaced by `<redacted>` in every output record. Added to `defaults.redact`. |

### `cloudscripts`

An allow list: `client execute-cloud-script` refuses any function not listed for the
title, before sending anything. A plain list (`cloudscripts: [getPlayerState]`) allows
names with default settings; a map sets them per function:

| Key | Default | Meaning |
|---|---|---|
| `description` | `""` | Free text. |
| `writes` | `true` | `false` marks a read-only function: it still runs under `--dry-run`. Leave `true` for anything that may change data. |
| `parameter` | `{}` | The `FunctionParameter`, with placeholders (see Placeholders and `--var`). `--params JSON` can add one-off fields on the command line. |

`pfcli titles` lists the allowed functions per title and the placeholders each takes.

### `player`: create, update and read players the title's way

Some titles cannot use a bare login to create a player: the game creates players through
CloudScript or a sequence of calls that sets up their data, and reads them back through
its own functions. The `player` block describes those sequences, so pfcli does it the
same way:

| Sequence | Command | Access |
|---|---|---|
| `create` | `client create-player` | READ WRITE: logs in with `CreateAccount`, saves the session, then runs the steps |
| `update` | `client update-player` | READ WRITE: runs the steps as a logged-in player |
| `state` | `client get-player-state` | READ ONLY: every step must be a read, checked before sending |

Each sequence is `{description, steps: [...]}`. Steps run in order and stop at the first
failure; each prints one output record (with `sequence` and `step`). A step is one of:

| Step | Meaning |
|---|---|
| `cloudscript: NAME` (+ optional `parameter`) | Run a function from the title's `cloudscripts` allow list. `parameter` is merged over the function's own. |
| `call: Family/Endpoint` + `body` | Call a registered endpoint. `Client/...` runs as the player; `Server/...` and `Admin/...` use the title secret key. |

The example above mixes both kinds: `create` seeds data with a Server call and sets the
name with a Client call, `update` goes through the title's CloudScript, and `state` reads
with two Client calls. A title can equally use one function for several sequences (e.g.
a settings function that also initializes a new player), or only endpoint calls.

```bash
pfcli --config pfcli-config-acme.yml client create-player GAME-DEV -u tester-01 --var name=Tester --var color=blue
pfcli --config pfcli-config-acme.yml client update-player GAME-DEV -u tester-01 --var color=green
pfcli --config pfcli-config-acme.yml client get-player-state GAME-DEV -u tester-01
``` On a title with a `create`
sequence, `client login-with-custom-id --create-account` refuses (it would make an
incomplete player) unless `--skip-create-steps` is given.

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
 "at": "2026-01-31T12:00:00Z", "request": {"StatisticName": "score", "StartPosition": 0, ...},
 "response": {"code": 200, "status": "OK", "data": {"Leaderboard": [...], "Version": 3}}}
```

- `at` is the UTC time of the call. Commands with input rows add `input`; client
  commands add `customId`.
- A command that makes several calls (pages, several titles) prints several lines.
- PlayFab errors are printed the same way (`response` is PlayFab's error reply); a message
  also goes to stderr and the exit status is 1.
- A write sent with `--dry-run` prints its envelope with `"dryRun": true` and
  `"response": null`.
- `--raw` prints only `response`, exactly as PlayFab returned it.
- Commands that make no PlayFab call (`titles`, `client sessions ...`) print one JSON line
  per record.

### `--output-format`: reshape any command's output

`--output-format NAME|PATH` (`-o`, a global option, before the command) passes every
record through an **output format file** instead. It works with every command; formats
are not tied to one. A bare `NAME` is looked up as `output-formats/NAME.yml` next to the
config file, then in this tool's folder; anything with a `/` or ending in `.yml` is used
as a path.

### Built-in and user formats

- **Built-in formats** ship with pfcli in `output-formats/` (committed, generic, listed
  below). Use them by name, e.g. `-o leaderboard-names`.
- **User formats** are yours: name them **`user-<name>.yml`** (e.g.
  `user-acme-leaderboard-names.yml`) and use them as `-o user-<name>`. Every `user-*`
  file is **gitignored**, so client-specific patterns, keys and names stay local. To
  customize a built-in format, copy it to a `user-` name and edit the copy.
- Anything **not** starting with `user-` is treated as built-in and can be committed: keep
  client specifics out of it.

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
| `fields` | Output name to JMESPath expression. Evaluated on the record plus `row` (the current item). Without `fields`, the item itself (or the record) is printed. Lists and objects in csv/tsv/text cells are written as JSON; booleans as `true`/`false`. |
| `drop_empty` | Fields that must not be empty (null, `""`, `[]`, `{}`). |
| `exclude` | Field to list of Python regexes (`re.search`, case-sensitive; add `(?i)` to ignore case). A match drops the row. Use single quotes in YAML so backslashes survive. |
| `unique` | Fields whose combination may appear only once; the first row wins. |
| `description` | Free text. |

Besides JMESPath's built-in functions, formats can use:

- `to_entries(obj)`: `{a: 1}` becomes `[{key: "a", value: 1}]` (like jq), for one row
  per key of a map such as TitleData or UserData.
- `from_json(str)`: parses a JSON string value (TitleData and UserData values are
  strings); a non-JSON string is returned unchanged.

The format applies to whatever would otherwise be printed: with `--raw`, expressions see
PlayFab's response instead of the envelope. Unknown keys, bad expressions and bad regexes
are reported before any call is made.

Built-in formats:

| Name | What it prints |
|---|---|
| `leaderboard-names` | CSV of unique display names per title from `server get-leaderboard`, with blanks and default-looking names removed. |
| `leaderboard-entries` | One JSON line per leaderboard entry (title, statistic, position, playFabId, name, value). |
| `data` | Only the `data` of each PlayFab response. |
| `titles-table` | `titles` as TSV. |
| `title-data-rows` | `server get-title-data` as CSV: at, title, key, value. |
| `player-summary` | `get-player-combined-info` (server or client) as CSV: title, playFabId, displayName, created, lastLogin, error. |
| `sessions-table` | `client sessions list` / `flush` as TSV. |

## Commands

Global options (before the command): `--config`, `--secrets`, `--sessions`,
`--output-format`/`-o`, `--raw`, `--log-level`. `ALIAS...` means one or more title aliases.
Commands that call PlayFab are grouped by PlayFab API family (`server ...`, `client ...`;
`admin` will follow) and named after the endpoint they call. Command options go after
the command name. Run `uv run pfcli.py <command> --help` for details.

### Local

| Command | Access | What it does |
|---|---|---|
| `titles` | READ ONLY (none) | One record per configured title: alias, titleId, host, key (`set (file)`, `set (env)`, `EMPTY`), allowed CloudScript functions and description. The config and secrets files used are reported on stderr. |

### `server`: Server API, title secret key

| Command | Access (endpoint) | What it does |
|---|---|---|
| `server get-leaderboard ALIAS... -s STAT` | READ ONLY (`Server/GetLeaderboard`) | Reads a legacy leaderboard (statistic) for **each title given**, paging 100 at a time, with display names. One record per page. `--max N` (default 100), `--start N`, `--version N` (default: current), `--pause`. Warns on stderr when a board is empty (PlayFab returns an empty board for a statistic that does not exist). |
| `server get-title-data ALIAS... [-k KEY]...` | READ ONLY (`Server/GetTitleData`) | TitleData key/value pairs, one record per title. No `-k` = all keys. Keys that do not exist are reported on stderr. |
| `server get-player-combined-info ALIAS... [-p ID]... [-i FILE\|-] [-r TEMPLATE]` | READ ONLY (`Server/GetPlayerCombinedInfo`) | Bulk player lookup: one record per player per title, with the input row under `input`. Players from `--playfab-id` and/or `--input` (see Input rows); `--id-column` names the column holding the PlayFab ID; `--request` picks what to fetch (see Request templates; default: profile with display name); `--concurrency N` (default 5). |

### `client`: Client API, as a logged-in player

See **Client API: player sessions** below for the two-step model.

| Command | Access (endpoint) | What it does |
|---|---|---|
| `client login-with-custom-id ALIAS... -u ID... [-i FILE\|-] [--create-account]` | **READ WRITE** (`Client/LoginWithCustomID`) | Step 1: logs players in and saves their sessions. Tickets are `<redacted>` in output. `--dry-run` sends nothing and saves nothing. On a title with a `player.create` sequence, `--create-account` refuses unless `--skip-create-steps`. |
| `client get-leaderboard ALIAS... -u ID... -s STAT` | READ ONLY (`Client/GetLeaderboard`) | A leaderboard as the player sees it; same options and paging as the server version. |
| `client get-player-profile ALIAS... -u ID... [-p OTHER]...` | READ ONLY (`Client/GetPlayerProfile`) | The player's own profile, or other players' with `--playfab-id`. |
| `client get-user-data ALIAS... -u ID... [-p OTHER]... [-k KEY]...` | READ ONLY (`Client/GetUserData`) | UserData, own or others' (PlayFab returns only what each value's permission allows). |
| `client get-account-info ALIAS... -u ID... [-p OTHER]...` | READ ONLY (`Client/GetAccountInfo`) | Account info, own or others'. |
| `client get-player-combined-info ALIAS... -u ID... [-p OTHER]... [-r TEMPLATE]` | READ ONLY (`Client/GetPlayerCombinedInfo`) | Same request templates as the server version, so answers can be compared. |
| `client update-user-title-display-name ALIAS... -u ID... -n NAME` | **READ WRITE** (`Client/UpdateUserTitleDisplayName`) | Changes the player's display name. Try `--dry-run` first. Many titles block this call for players (403 `NotAuthorizedByTitle`) and change names through CloudScript instead. |
| `client execute-cloud-script ALIAS... -u ID... -f FUNCTION [--var K=V]...` | **READ WRITE** (`Client/ExecuteCloudScript`) | Runs a classic CloudScript function as the player. Only functions allowed for the title in the config (`cloudscripts`); `--var` fills its placeholders; `--params JSON` adds one-off fields; `--revision N`, `--playstream-event`. A CloudScript error (`data.Error`) or an error-shaped `FunctionResult` is reported on stderr with exit 1. `--dry-run` sends nothing except functions marked `writes: false`. |
| `client create-player ALIAS... -u ID... [--var K=V]...` | **READ WRITE** (login, then the title's `player.create` steps) | Creates players the title's way. An existing custom ID is left alone (exit 1; use `update-player`). `--dry-run` shows every step. |
| `client update-player ALIAS... -u ID... [--var K=V]...` | **READ WRITE** (the title's `player.update` steps) | Updates logged-in players the title's way, e.g. `--var name=NewName`. |
| `client get-player-state ALIAS... -u ID...` | READ ONLY (the title's `player.state` steps) | Reads players the title's way; refuses a sequence with any writing step. |
| `client sessions list [VALUE...] [-t ALIAS]... [--expired]` | READ ONLY (none, local) | Saved sessions, tickets redacted. |
| `client sessions flush [VALUE...] [-t ALIAS]... [--expired] [--all]` | **LOCAL WRITE** (none, local) | Removes saved sessions. Needs a selector or `--all`; `--dry-run` previews. |

Client output records also carry `customId` (whose session made the call).

### Examples

```bash
# Raw leaderboard pages, for jq or later processing
uv run pfcli.py --config pfcli-config-acme.yml \
  server get-leaderboard GAME-PROD GAME-DEV -s score --max 5000 > score.ndjson

# Names list as CSV
uv run pfcli.py --config pfcli-config-acme.yml -o leaderboard-names \
  server get-leaderboard GAME-PROD GAME-DEV -s score --max 5000 > names.csv

# TitleData snapshot, one CSV row per key, appended to a log
uv run pfcli.py --config pfcli-config-acme.yml -o title-data-rows \
  server get-title-data GAME-PROD -k LastWinner >> winners.csv

# Create a test player the title's way, change its name, read it back
uv run pfcli.py --config pfcli-config-acme.yml client create-player GAME-DEV -u audit-001 --var name=Tester
uv run pfcli.py --config pfcli-config-acme.yml client update-player GAME-DEV -u audit-001 --var name=Tester2 --dry-run
uv run pfcli.py --config pfcli-config-acme.yml client get-player-state GAME-DEV -u audit-001

# Run one allowed CloudScript function directly
uv run pfcli.py --config pfcli-config-acme.yml client execute-cloud-script GAME-DEV \
  -u audit-001 -f savePlayerSettings --var color=blue --dry-run

# Leaderboard top 100 -> each player's profile (pfcli piped into pfcli)
uv run pfcli.py --config pfcli-config-acme.yml -o leaderboard-entries \
  server get-leaderboard GAME-PROD -s score --max 100 \
| uv run pfcli.py --config pfcli-config-acme.yml -o player-summary \
  server get-player-combined-info GAME-PROD -i - --id-column playFabId -r player-basics
```

Notes:
- A board can return fewer rows than `--max` when fewer players have that statistic.
- The current version of a statistic is read unless `--version` is given, so a daily or
  hourly statistic gives the current day's or hour's board.

## Input rows

Commands that work on many players take rows from repeatable options (`--playfab-id`,
`--custom-id`) and/or `--input FILE` (`-` = stdin):

- **CSV** with a header row, or **NDJSON** (one JSON object per line; detected when the
  input starts with `{`). NDJSON means pfcli's own output, reshaped with a format, can be
  piped straight into another pfcli command.
- `--id-column NAME` says which column holds the ID when it is not named `PlayFabId`
  (or `CustomId` for logins), e.g. `--id-column playFabId` for `leaderboard-entries` output.
- The input row is added to each output record as `input`, so formats can combine input
  columns with response fields.

## Placeholders and `--var`

Every request body pfcli builds from YAML (request templates, CloudScript parameters,
player sequence steps) uses the same placeholders. A string value that is **exactly** one
of these is replaced:

| Placeholder | Filled from |
|---|---|
| `$.column` | the current `--input` row |
| `$session`, `$playFabId`, `$customId`, `$titleId` | the saved player session and the title (reserved; `--var` cannot set them) |
| `$NAME` | `--var NAME=VALUE` (repeatable); required: a missing value stops the run before anything is sent |
| `$NAME?` | the same, but optional: without a value, the key (or list item) is left out |

Inside a one-line `{ ... }` map, quote optional placeholders (`name: "$name?"`): YAML
reads a bare `?` there as syntax. On their own line (`name: $name?`) no quotes are needed.

Session tickets are shown as `<redacted>` wherever they appear in output: in requests,
and in responses that echo them back (some CloudScripts do). Add a title's own
credentials (e.g. login keys) to its `redact` list.

### Command-line options or a request object?

pfcli follows one rule: **the command line supplies values; it never builds structure.**

1. **Options** for requests PlayFab defines that are small and flat (about four fields or
   fewer, plain values or simple lists), and that change from run to run: `-s STAT`,
   `-k KEY`, `-n NAME`.
2. **A request template** (`-r`) for requests that are nested, have many optional switches,
   or are worth saving and reusing (e.g. GetPlayerCombinedInfo's InfoRequestParameters).
3. **The config** for request shapes **the title defines**, not PlayFab: CloudScript
   parameters and player sequences. They are named once per title in your own config.
4. Values for any of these come from `--var NAME=VALUE`, input rows (`$.column`) or the
   session. `--params JSON` on `execute-cloud-script` is an override for one-off fields.

## Request templates

A request template is a PlayFab request body in YAML, chosen with `--request NAME|PATH`
(`-r`), using the placeholders above (`$.column` per input row, `$NAME` from `--var`). All
bodies are built before the first call, so a missing value stops the run before anything
is sent.

```yaml
# request-templates/player-basics.yml
PlayFabId: $.PlayFabId
InfoRequestParameters:
  GetPlayerProfile: true
  ProfileConstraints: { ShowDisplayName: true, ShowLastLogin: true }
  GetUserData: true
  UserDataKeys: [progress, settings]
CustomTags:
  batch: $.batchTag          # any input column can go anywhere
```

Lookup and naming are the same as output formats: `request-templates/NAME.yml` next to
the config, then in this tool's folder; a path is used as given. Built-in templates are
committed (`player-basics`); **your own are `user-<name>.yml` and gitignored**. The
PlayFab REST reference describes every request field.

## Client API: player sessions

Client commands act **as a player**, using the player's session instead of the title
secret key. They show what a game client (or anyone holding a player's ticket) can see and
do. It takes **two steps**:

1. **Log in once** per player and title. This saves the session (ticket, PlayFab ID,
   login time):
   ```bash
   uv run pfcli.py --config pfcli-config-acme.yml client login-with-custom-id GAME-PROD -u audit-001
   ```
2. **Run any client command** as that player with the same `--custom-id` (`-u`). It uses
   the saved session and never logs in by itself:
   ```bash
   uv run pfcli.py --config pfcli-config-acme.yml client get-player-profile GAME-PROD -u audit-001 -p <OTHER_ID>
   ```

Details:

- **Sessions file:** `pfcli-sessions[-<client>].yml`, paired with the config like the
  secrets file (`--sessions` overrides), written `chmod 600`, gitignored by the `pfcli*.yml`
  pattern. Sessions are per title and custom ID; logging in again replaces one.
- **Tickets are credentials:** pfcli never prints them (`<redacted>` in login output and
  in `sessions list`).
- **Expiry:** a session lasts about 24 hours. A session older than that, or one PlayFab
  rejects (it is then marked expired), is skipped with a message on stderr telling you to
  log in again; the exit status is 1.
- **Several players and titles:** `-u` is repeatable and `ALIAS...` takes several titles;
  each needs its own login.
- **Login is READ WRITE:** `--create-account` can create players, and any login can
  trigger the title's login automations or CloudScript. Use `--dry-run` to see the
  requests first. Without `--create-account`, an unknown custom ID fails with
  `AccountNotFound`.
- **Flushing sessions** (`client sessions flush`) only stops pfcli from using them; the
  ticket stays valid at PlayFab until it expires. Select sessions by any VALUE (custom ID,
  PlayFab ID, title alias or title ID), narrow with `--title`, pick `--expired`, or use
  `--all`; `--dry-run` previews. `client sessions list` takes the same selectors.

## Access and safety

pfcli is **not** read-only by design. What a command can do on a title is decided by the
credentials you give it (a title secret key has full Server and Admin access); pfcli's
job is to make each command's effect obvious:

- **Every command is tagged** `READ ONLY`, `READ WRITE` or `LOCAL WRITE`, shown in
  `pfcli --help` and at the top of the command's own `--help`, together with the PlayFab
  endpoints it calls. `LOCAL WRITE` changes only a local pfcli file (e.g. flushing
  sessions) and calls no PlayFab endpoint.
- **Endpoints are named by API family**, as in PlayFab's REST API: `Server/...`,
  `Admin/...`, `Client/...`. Each is registered in `ALLOWED_ENDPOINTS` (`lib/client.py`)
  as `read` or `write`; an unregistered endpoint raises before any request is sent.
- **Every `READ WRITE` and `LOCAL WRITE` command has `--dry-run`**: writes are shown, not
  made; reads still run so the output shows what would change.
- Declarations are checked when pfcli starts: a `READ ONLY` command that lists a write
  endpoint, or a `READ WRITE` command with none, fails immediately.

Things to keep in mind:

- A title secret key reaches live data directly; try a write with `--dry-run` first.
- `Client/...` endpoints need a player session, not the secret key. A Client login (e.g.
  `LoginWithCustomID`) can create players or trigger the title's login CloudScript,
  which can write data. That is why `client login-with-custom-id` is READ WRITE and the
  other client commands never log in by themselves (see Client API: player sessions).
- Session tickets are credentials, like secret keys: pfcli never prints them, even when a
  response echoes them back. A title's own credentials go in its `redact` list.

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
   `ctx.obj.emitter`, `ctx.obj.sessions`, `ctx.obj.root`. Commands calling an API family go
   in that family's group (`server`, `client`, later `admin`), named after the endpoint in
   kebab-case. Client commands pass `notes=SESSION_NOTES` (from
   `lib/commands/client/common.py`) so their help explains the two-step session model,
   and use `for_each_session(...)` to find sessions.
2. Register each new endpoint in `ALLOWED_ENDPOINTS` with its family and `READ`/`WRITE`.
3. Call PlayFab through `TitleClient(config.title(alias)).call("Server/<Name>", body,
   dry_run=dry_run)` (Server/Admin) or `PlayerClient(...).call("Client/<Name>", body,
   session_ticket, dry_run=dry_run)` (Client). It returns the envelope with PlayFab's reply (errors included);
   pass it to `ctx.obj.emitter.emit(...)`, check it with `ok(env)`, and write any
   message to stderr. Never print data any other way: formats only see emitted records.
4. Register the command in `pfcli.py` (`cli.add_command(...)` or
   `server.add_command(...)`) and add it to the Commands table above.
5. If it needs new config keys, read them in `lib/config.py`, add them to
   `pfcli-config.example.yml`, and document them in the config reference above.
6. Dependencies: `uv add <package>`, never `pip install`.
