# Agent instructions, python-playfab-cli

Describes the **current** state; correct it rather than appending history.

## What this is

`pfcli`, Eric's generic, read-only PlayFab CLI. One Click entry point (`pfcli.py`)
with a module per command in `lib/commands/`. Titles and settings live in a YAML config,
secret keys in an env file. Defaults are `pfcli.yml` and `.env`; per client, use
`pfcli-config-<client>.yml` and `pfcli-secrets-<client>.env`, passed explicitly with
`--config` and `--env`. All of these are gitignored and machine-local; only
`pfcli.example.yml` and `.env.example` are committed. Read `README.md` first.

Eric intends this to become the single CLI for his other PlayFab tools over time
(`python-playfab-retrieve-player`, `python-playfab-auditor`, `python-playfab-titledata-pull`
in this same `projects/ericwastaken/` folder). Fold them in as commands, not side scripts.

## House rules

- **Generic only.** No client, studio, park or game names in code, comments, README or
  examples. Anything client-specific belongs in the gitignored
  `pfcli-config-<client>.yml` / `pfcli-secrets-<client>.env`.
- **Ignore by pattern.** `.gitignore` ignores every `pfcli*.yml|yaml` and every
  `.env` / `.env.*` / `*.env`, re-including only `pfcli.example.yml` and `.env.example`.
  Keep new config/secrets names inside those patterns; do not add per-file ignore lines.
- **Read-only by default.** `lib/client.py` enforces `ALLOWED_READS`. Never add a write
  endpoint unless Eric asks for that exact capability, and then as an explicit,
  separately named, confirm-before-run command.
- **No Client API for data pulls.** A client login can create players or run the title's
  login CloudScript, which writes.
- **uv only.** `uv sync`, `uv run pfcli.py ...`, `uv add <pkg>`. Never `pip install`
  into the global Python.
- **Secrets.** Never print a key; report "set/EMPTY" (the `titles` command) or at most the
  last 4 characters. Keep `.env` at `chmod 600`.
- The `.venv` is not portable: after moving the folder, delete `.venv` and `uv sync`.

## Known traps

- Some titles live on a **dedicated cluster** with its own host; the shared host returns
  `InvalidAPIEndpoint`. Set `host` per title in `pfcli.yml`.
- The Claude in Chrome extension **blocks returning secret values** from Game Manager's
  Secret Keys page. Do not work around it; ask Eric to paste the key into `.env`.
- Default display names differ per title (language, separator). Set
  `default_name_patterns` per title, or `names-report` will count defaults as known-good.

## State (2026-11-10)

Created 2026-11-10. Local git repo on `main` with an initial commit; no remote yet.
Commands: `titles`, `leaderboard-names`, `names-report`, all verified against live titles.
