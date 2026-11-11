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
   specific action. Approval for one write is not approval for the next. Only add `--yes`
   (needed for >10 targets, several titles, or any deletion) after the user approved that
   exact run. Never run a deletion (`delete-player`, `delete-master-player-account`)
   unless the user named the players and confirmed.
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

## Bootstrap mode (no config yet, or "set up pfcli")

Enter this mode when the pfcli folder has no `pfcli-config-*.yml`, or the user asks to set
pfcli up or add titles. Interview the user **one question at a time**, explaining where each
fact is in PlayFab, then let `pfcli init` write the files.

1. **Project label**: a short lowercase name for this set of titles (e.g. `acme`). It names
   the files `pfcli-config-acme.yml` and `pfcli-secrets-acme.yml`.
2. **Titles**, for each one:
   - **Alias**: a short name they'll type (e.g. `GAME-DEV`, `GAME-PROD`).
   - **Title ID**: in Game Manager it's on the title's card on the studio page, in the URL
     (`.../t/<TITLE_ID>/...`), and under the title's Settings (gear) > Title settings.
     4-10 hex characters.
   - **Description**: e.g. "Our game, production".
   - **Dedicated cluster?** If their Game Manager address is
     `developer.<cluster>.playfab.com` (not `developer.playfab.com`), the title needs
     `--host ALIAS=https://{title_id}.<cluster>.playfabapi.com`.
3. **Secret keys needed?** Only for `server` / `admin` commands. Player-only (`client`) use
   needs none.
4. **Show the plan, then create** (LOCAL WRITE; dry-run first, then run after a yes):
   ```bash
   pfcli init acme --title GAME-DEV=ABCD2 --title GAME-PROD=ABCD1 \
     --description GAME-DEV="Our game, dev" --dry-run
   ```
   Add titles to an existing pair later with `pfcli init acme --add-title ALIAS=TITLE_ID`.
5. **Secrets hand-off (never handle keys yourself).** Tell the user to:
   - create a **dedicated** key: Game Manager > the title > Settings (gear) > Title settings >
     Secret Keys > New secret key (name it e.g. "pfcli");
   - open `pfcli-secrets-acme.yml` in **their own editor** and paste each key between the
     quotes next to its title ID, then save.

   Do not open, read or edit the secrets file. If the user pastes a key into the chat, tell
   them not to, and recommend disabling that key and creating a new one (it's now in the
   transcript).
6. **Verify**: `pfcli --config pfcli-config-acme.yml titles --verify`. It makes one harmless
   call per title (asks for TitleData that doesn't exist). Explain any failure: `skipped: no
   secret key` (fine for client-only titles), `secret key was rejected` (wrong or disabled
   key, or pasted under the wrong title ID), `InvalidAPIEndpoint` (dedicated cluster: set
   `--host`, or the title ID is wrong).
7. **Next**: suggest a first READ ONLY command (e.g. a leaderboard) and point to the user
   guide. Offer the advanced, game-specific config (CloudScript allow list, player
   sequences, `redact`) only if the user needs client-side game flows.

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

Start every session by checking the setup (safe; prints no secrets). If there's no config
yet, use **Bootstrap mode** above.

```bash
pfcli --config pfcli-config-acme.yml -o titles-table titles
pfcli --config pfcli-config-acme.yml titles --verify     # one harmless live call per title
```

---

## Commands

`ALIAS...` = one or more title names from the config (each runs with its own host and key;
one failing title doesn't stop the others; exit status 1 if any failed).

| Command | Access | Use for |
|---|---|---|
| `init NAME --title ALIAS=ID... [--description ALIAS=TEXT] [--host ALIAS=URL]` / `init NAME --add-title ALIAS=ID` | LOCAL WRITE | Create a config + empty secrets pair (or add titles); see Bootstrap mode |
| `titles [--verify]` | READ ONLY | Titles, key status (`set`/`EMPTY`), allowed CloudScript, player sequences; `--verify` proves host + key with one harmless call per title |
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

**More `server` / `admin` / `client` endpoint commands** (one PlayFab call each; same
patterns: `ALIAS...`, `-p ID...` or `--input` for Server/Admin, `-u ID...` for Client):
friends (`get-friends-list`, `add-friend`, `remove-friend`), `update-avatar-url`,
`admin update-user-title-display-name` (skips the game's name checks), tags
(`get-player-tags`, `add-player-tag`, `remove-player-tag`), `consume-item`,
`add-user-virtual-currency` / `subtract-user-virtual-currency`, `get-catalog-items`,
`get-leaderboard-around-user` (client: `-around-player`), `get-user-account-info`,
`get-all-segments`, `get-player-segments`, `admin export-players-in-segment` /
`get-segment-export`, and deletions `delete-player` / `admin delete-master-player-account`
(always `--yes`). Run `pfcli server --help`, `pfcli admin --help`, `pfcli client --help`.

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
| `key EMPTY` / `no secret key for title` | The secrets file has no key for that title ID; ask the user to add it in their editor (never ask them to paste it to you) |
| `No titles defined` | New config: add titles with `pfcli init NAME --add-title ALIAS=TITLE_ID` |
| `(hint: ... secret key was rejected ...)` | Wrong/disabled key or wrong title ID in the secrets file; run `titles --verify` |
| `InvalidAPIEndpoint` | Title is on a dedicated cluster: add `host` to the title in the config |
| `No such option` | Global vs command option placement |
| `no saved session` / `session ... has expired` | Run the login command pfcli prints (a write: ask first) |
| `AccountNotFound` | No player with that custom ID; don't create one without asking |
| `403 NotAuthorizedByTitle` | The title's API policy blocks that call for players; report it, don't work around it |
| `CloudScript function ... is not allowed` | Not in the title's `cloudscripts` list; ask before adding it |
| `no value for $name` | Add `--var name=VALUE` |
| `function returned an error` / `CloudScript error` | The game's script failed or rejected the input; full reply is in the output |
| write `NOT retried ... may or may not have been applied` | Stop; tell the user to check the title |
