---
name: pfcli
description: Use pfcli, an unofficial command-line tool for Microsoft PlayFab titles, safely on a user's behalf - read leaderboards, title data and players, act as a test player through the Client API, run allowed CloudScript and player sequences, and reshape PlayFab's JSON output.
---

# Use pfcli (unofficial PlayFab CLI)

Use this skill when a user asks you to read or work with data in their **PlayFab** titles
with pfcli: leaderboards, TitleData, player lookups, acting as a test player, running their
game's CloudScript, or producing CSV/JSON from PlayFab.

> pfcli is **not affiliated with Microsoft or Azure PlayFab**. It uses the user's own keys and
> logins against live game backends. You are operating on real data for real players: follow
> the safety rules below without exception.

User guide (full reference): https://ericwastaken.github.io/playfab-cli-unofficial/
If you are asked to change pfcli's **code**, read `AGENT.md` in the repository instead.

---

## Safety rules for agents (always)

1. **Never read, print, copy or paste secrets.** Do not open or display
   `pfcli-secrets-*.yml`, `pfcli-sessions-*.yml`, `.env` files, or the values of
   `PFCLI_SECRET_*` variables. To check keys, run `titles` (it shows only `set`/`EMPTY`).
   Never put keys or session tickets in chat, files, commits, issues or commands you echo.
2. **Read-only by default.** Every command's help starts with `[READ ONLY]`,
   `[READ WRITE]` or `[LOCAL WRITE]`. You may run READ ONLY commands when asked.
3. **Before any READ WRITE command**: run it with `--dry-run` first, show the user exactly
   what would be sent (title, player, endpoint, body), and get an explicit yes for that
   specific action. Approval for one write is not approval for the next.
4. **Prefer development titles and test players.** Ask before touching a production title
   or a real player's account. Logging in (`client login-with-custom-id`,
   `client create-player`) is a write: it can create players and trigger the title's login
   automations.
5. **Never retry a failed write on your own.** If pfcli says a write got a server error and
   "may or may not have been applied", stop and tell the user.
6. **Treat output as personal data** (display names, PlayFab IDs, user data). Keep only the
   fields needed (use `-o` formats), don't paste large dumps into chat, and don't save output
   outside the places the user asked for.
7. **Don't commit or share the user's files**: `pfcli-config-*`, `pfcli-secrets-*`,
   `pfcli-sessions-*`, `output-formats/user-*`, `request-templates/user-*`. Put anything
   project-specific in those files, never in pfcli's built-in files.
8. **Clean up sessions** you created when the task is done: offer to run
   `client sessions flush <custom-id>` (a flushed ticket stays valid at PlayFab until it
   expires, about 24 h).

---

## Find and run pfcli

pfcli runs from its cloned folder with uv:

```bash
cd <path>/playfab-cli-unofficial      # the folder with pfcli.py
uv run pfcli.py --help
```

If it isn't installed and the user agrees:

```bash
git clone https://github.com/ericwastaken/playfab-cli-unofficial.git
cd playfab-cli-unofficial && uv sync
```

The user's config is usually `pfcli-config-<name>.yml` in that folder; ask which one if
there are several. Below, `pfcli` means `uv run pfcli.py`.

**Option placement:** global options go **before** the command; command options **after**:

```bash
pfcli --config pfcli-config-acme.yml -o leaderboard-entries server get-leaderboard GAME-PROD -s score --max 100
```

Start every session by checking the setup (safe; prints no secrets):

```bash
pfcli --config pfcli-config-acme.yml -o titles-table titles
```

---

## Commands

`ALIAS...` = one or more title names from the config (each runs with its own host and key;
one failing title doesn't stop the others; exit status 1 if any failed).

| Command | Access | Use for |
|---|---|---|
| `titles` | READ ONLY | Titles, key status (`set`/`EMPTY`), allowed CloudScript, player sequences |
| `server get-leaderboard ALIAS... -s STAT [--max N] [--start N] [--version N]` | READ ONLY | Leaderboards (pages of 100). Statistic names are case-sensitive; an empty board usually means a wrong name |
| `server get-title-data ALIAS... [-k KEY]...` | READ ONLY | TitleData |
| `server get-player-combined-info ALIAS... [-p ID]... [-i FILE\|-] [--id-column COL] [-r TEMPLATE] [--var K=V]` | READ ONLY | Player details in bulk |
| `client login-with-custom-id ALIAS... -u ID... [--create-account]` | READ WRITE | Log a player in and save the session (step 1 for all client commands) |
| `client create-player / update-player ALIAS... -u ID... [--var K=V]` | READ WRITE | The title's own create/update sequence (from the config) |
| `client get-player-state ALIAS... -u ID...` | READ ONLY | The title's own read sequence |
| `client execute-cloud-script ALIAS... -u ID... -f FUNCTION [--var K=V]` | READ WRITE | Run a CloudScript function the config allows |
| `client get-leaderboard / get-player-profile / get-user-data / get-account-info / get-player-combined-info ALIAS... -u ID... [-p OTHER]` | READ ONLY | What a player can see (own data, or other players with `-p`) |
| `client get-title-data ALIAS... -u ID... [-k KEY]` / `client get-catalog-items ALIAS... -u ID... [-c VERSION]` | READ ONLY | TitleData / catalog as a game client sees them |
| `client update-user-title-display-name ALIAS... -u ID... -n NAME` | READ WRITE | Direct name change (often blocked by title policy: 403) |
| `client sessions list [VALUE...]` | READ ONLY | Saved sessions (tickets redacted) |
| `client sessions flush VALUE... \| --title A \| --expired \| --all` | LOCAL WRITE | Remove saved sessions |

Client commands need a saved session from step 1 with the same `-u`; they never log in by
themselves. Run `pfcli <group> <command> --help` for every option.

---

## Output

- **stdout = data only**; messages and errors go to stderr. Redirect with `>` or pipe to
  `jq`.
- **Default:** one JSON line per PlayFab call: `{title, titleId, endpoint, at, request,
  response}`; `response` is PlayFab's reply unchanged (errors included). `--raw` prints only
  `response`.
- **Formats** (`-o NAME`): `leaderboard-names`, `leaderboard-entries`, `title-data-rows`,
  `player-summary`, `titles-table`, `sessions-table`, `catalog-items`, `data`; users' own are `user-<name>`.
  To create one, write `output-formats/user-<name>.yml` with `format`, `rows`, `fields`
  (JMESPath; `row` is the current item), `drop_empty`, `exclude`, `unique`. Functions
  `to_entries()` and `from_json()` are available.
- Session tickets and the title's `redact` patterns always appear as `<redacted>`.

---

## Values and config

- **Placeholders** in request templates, CloudScript parameters and sequence steps:
  `$.column` (input row), `$session`, `$playFabId`, `$customId`, `$titleId` (from the
  session), `$NAME` (required `--var NAME=VALUE`), `$NAME?` (optional). Quote optional ones
  inside one-line maps: `{ name: "$name?" }`.
- **The command line supplies values, never structure.** Small requests take options;
  nested ones take a request template (`-r`, files in `request-templates/`, the user's own
  named `user-<name>.yml`); game-defined shapes live in the user's config.
- **Game-specific config** (only in the user's `pfcli-config-<name>.yml`, never in
  committed files): per title `cloudscripts` (allow list with `writes`, `parameter`),
  `player.create|update|state` (steps: `cloudscript: NAME` or `call: Family/Endpoint` +
  `body`), and `redact` (regex list for game credentials). Several titles of one game can
  share blocks with YAML anchors (`&name` / `*name`), but only if each title's live
  CloudScript has those functions. Show the user any config change before saving it.

---

## Common errors

| Message | Meaning / action |
|---|---|
| `key EMPTY` / `no secret key for title` | The secrets file has no key for that title ID; ask the user to add it (never ask them to paste it to you) |
| `InvalidAPIEndpoint` | Title is on a dedicated cluster: add `host` to the title in the config |
| `No such option` | Global vs command option placement |
| `no saved session` / `session ... has expired` | Run the login command pfcli prints (a write: ask first) |
| `AccountNotFound` | No player with that custom ID; don't create one without asking |
| `403 NotAuthorizedByTitle` | The title's API policy blocks that call for players; report it, don't work around it |
| `CloudScript function ... is not allowed` | Not in the title's `cloudscripts` list; ask before adding it |
| `no value for $name` | Add `--var name=VALUE` |
| `function returned an error` / `CloudScript error` | The game's script failed or rejected the input; full reply is in the output |
| write `NOT retried ... may or may not have been applied` | Stop; tell the user to check the title |
