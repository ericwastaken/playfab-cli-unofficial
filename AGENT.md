# Agent instructions, python-playfab-cli

Describes the **current** state; correct it rather than appending history.

## What this is

`pfcli`, Eric's generic PlayFab CLI (read and write; each command is tagged). One Click
entry point (`pfcli.py`) with a module per command in `lib/commands/` (API-family groups
in subfolders, e.g. `lib/commands/server/`). It calls the PlayFab REST API directly
(urllib in `lib/client.py`); do not add the PlayFab SDK. Titles and settings live in a
YAML config, secret keys in a YAML secrets file keyed by title ID. Defaults are
`pfcli-config.yml` / `pfcli-secrets.yml`; per client, `pfcli-config-<client>.yml` /
`pfcli-secrets-<client>.yml`. `--config` alone is enough: the secrets file is found by
swapping `pfcli-config` for `pfcli-secrets` in the name (override with `--secrets`).
Fallback: env var `PFCLI_SECRET_<TITLE_ID>`. All real files are gitignored and
machine-local; only `pfcli-config.example.yml` and `pfcli-secrets.example.yml` are
committed. Read `README.md` first.

Eric intends this to become the single CLI for his other PlayFab tools over time
(`python-playfab-retrieve-player`, `python-playfab-auditor`, `python-playfab-titledata-pull`
in this same `projects/ericwastaken/` folder). Fold them in as commands, not side scripts.

## House rules

- **Generic only.** No client, studio, park or game names in code, comments, README or
  examples. Anything client-specific belongs in the gitignored
  `pfcli-config-<client>.yml` / `pfcli-secrets-<client>.yml`.
- **Ignore by pattern.** `.gitignore` ignores every `pfcli*.yml|yaml` (and any `.env`
  variant) plus `output-formats/user-*` and `request-templates/user-*`. Keep new config/secrets
  names starting with `pfcli` and ending `.yml`; do not add per-file ignore lines.
- **Not read-only; credentials decide.** pfcli may read and write; what it can do is
  governed by the credentials supplied. Every command uses `pf_command` with
  `READ ONLY` or `READ WRITE` and its endpoints; every `READ WRITE` command gets
  `--dry-run` (pass `dry_run` to each `call`). Register endpoints in `ALLOWED_ENDPOINTS`
  as `<Family>/<Name>` (Server/Admin/Client, as PlayFab names them) with READ/WRITE.
- **Output: stdout is data, stderr is everything else.** Every command emits records via
  `ctx.obj.emitter.emit(...)`; for PlayFab calls that is the envelope from
  `TitleClient.call()` with PlayFab's response untouched. Default output is NDJSON of
  those; `--raw` prints only the response; `-o/--output-format` reshapes any command's
  output with a format file from `output-formats/`. Never add command-specific output
  files or formats (Eric's rule); add a generic built-in format to `output-formats/`.
- **Built-in vs user files (Eric's rule).** Formats/templates that ship with pfcli are
  generic and committed (`output-formats/NAME.yml`, `request-templates/NAME.yml`). A
  user's own (client-specific) ones are `user-<name>.yml` and gitignored. Never give a
  client-specific file a name without the `user-` prefix.
- **Several titles per command (a feature Eric values).** Commands that call PlayFab
  take `ALIAS...` (one or more titles), call each with its own host and key, emit records
  tagged with `title`/`titleId`, skip a failing title with a stderr message and keep
  going, and exit 1 if any failed. New commands must follow the same pattern.
- **Client commands: two-step sessions (Eric's requirement).** `client
  login-with-custom-id` (READ WRITE) saves sessions; every other client command takes
  `--custom-id`, uses the saved session and never logs in by itself. The README and the
  `--help` of EVERY client command must explain this: pass `notes=SESSION_NOTES` to
  `pf_command`. Session tickets are credentials: never print them (use `sessions.redact`
  / `sessions.public`). `client sessions list|flush` manage the local file.
- **Inputs and templates.** Bulk commands take repeatable IDs plus `--input FILE|-`
  (CSV or NDJSON, so pfcli output pipes into pfcli) and `--request` templates from
  `request-templates/` (built-in) or `user-*` ones (gitignored).
- **Title-specific stays in user config (Eric's rule).** CloudScript function names,
  their parameter shapes and player sequences (`player.create|update|state`) are unique to
  a client/game: put them ONLY in the gitignored `pfcli-config-<client>.yml`. Committed
  files (README, `pfcli-config.example.yml`, code) use generic names (`savePlayerSettings`,
  `getPlayerState`).
- **Options vs request objects (Eric's rule).** The CLI supplies values, never structure:
  options for small flat PlayFab-defined requests; request templates for nested or
  many-switch ones; the config for title-defined shapes (CloudScript, player sequences);
  values via `--var NAME=VALUE`, `$.column` rows, or reserved session names
  (`$session $playFabId $customId $titleId`); `$NAME?` is optional. Resolver:
  `lib/inputs.resolve`.
- **Credentials never reach output.** Every client record is scrubbed (request AND
  response) of the session ticket it used, via `client.protect()`; some CloudScripts echo
  the ticket back. Title-specific credentials (e.g. a game's login keys) go in the title's
  `redact` regex list in the user config. New code that emits records must pass them
  through `protect()` (TitleClient/PlayerClient `call()` already do).
- **Player sequences.** `client create-player` (login CreateAccount + player.create steps),
  `update-player`, `get-player-state` (READ ONLY: refuses writing steps). Steps are
  `cloudscript: NAME` (must be in the allow list) or `call: Family/Endpoint` (must be in
  ALLOWED_ENDPOINTS; Server/Admin use the secret key). `login --create-account` refuses on
  titles with player.create unless `--skip-create-steps`.
- **CloudScript allow list.** `client execute-cloud-script` only runs functions listed
  under the title's (or defaults') `cloudscripts` in the config, checked before any call.
  `writes: false` marks read-only functions (they run under --dry-run). Parameter
  placeholders `$session`/`$playFabId`/`$customId` come from the saved session; tickets
  are scrubbed from echoed requests. CloudScript reports failures inside HTTP 200
  (`data.Error`, or an error-shaped `FunctionResult`); the command treats both as failure.
- **Access tags.** READ ONLY, READ WRITE (PlayFab writes) or LOCAL WRITE (changes a local
  pfcli file only); the last two get `--dry-run` automatically.
- **Command naming.** Commands that call PlayFab go in their API family's group
  (`server`, `client`, later `admin`) and are named after the endpoint in kebab-case.
- **Client API caution.** A Client login can create players or run the title's login
  CloudScript, which writes; say so when a command would use one.
- **uv only.** `uv sync`, `uv run pfcli.py ...`, `uv add <pkg>`. Never `pip install`
  into the global Python.
- **Secrets.** Never print a key; report "set/EMPTY" (the `titles` command) or at most the
  last 4 characters. Keep secrets files at `chmod 600` (pfcli warns otherwise).
- The `.venv` is not portable: after moving the folder, delete `.venv` and `uv sync`.

## Known traps

- Some titles live on a **dedicated cluster** with its own host; the shared host returns
  `InvalidAPIEndpoint`. Set `host` per title in the config.
- The Claude in Chrome extension **blocks returning secret values** from Game Manager's
  Secret Keys page. Do not work around it; ask Eric to paste the key into the secrets file.
- Default display names differ per title (language, separator). A names format's
  `exclude` must cover every title's pattern, or defaults pass as real names.
- PlayFab answers `GetLeaderboard` for a statistic that does not exist with success and
  an empty board; `server get-leaderboard` warns on stderr.
- JMESPath has no arithmetic: leaderboard `Position` stays 0-based in formats.

## State (2026-11-10)

Created 2026-11-10. Local git repo on `main`; no remote yet. Secrets moved from .env to
YAML (keyed by title ID) on 2026-11-10.
Commands: `titles`; `server get-leaderboard | get-title-data | get-player-combined-info`
(verified live); `client login-with-custom-id | get-leaderboard | get-player-profile |
get-user-data | get-account-info | get-player-combined-info |
update-user-title-display-name | execute-cloud-script | create-player | update-player |
get-player-state | sessions list | sessions flush`
(verified against a local
fake PlayFab server; not yet run against a real title).
