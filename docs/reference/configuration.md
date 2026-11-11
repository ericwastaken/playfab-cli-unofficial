# Config and secrets files

## Which files pfcli uses

| | Config | Secrets | Saved logins |
|---|---|---|---|
| Your files | `pfcli-config-<name>.yml` | `pfcli-secrets-<name>.yml` | `pfcli-sessions-<name>.yml` (created by pfcli) |
| Option | `--config` | `--secrets` | `--sessions` |
| Found automatically? | Default `pfcli-config.yml` | Yes, from the config's name, in the same folder | Yes, from the config's name |
| Example to copy | `pfcli-config.example.yml` | `pfcli-secrets.example.yml` | none |

All of your own files are private: Git ignores them. See [Files and Git](files-and-git.md).

## Config file

```yaml
defaults:                          # optional: applies to every title
  host: "https://{title_id}.playfabapi.com"

titles:
  GAME-DEV:                        # the name you type in commands
    title_id: ABCD2                # required
    description: Our game, development
    host: "https://{title_id}.your-cluster.playfabapi.com"   # only for dedicated clusters
    cloudscripts: { ... }          # see below
    player: { ... }                # see below
    redact: [ ... ]                # see below
```

| Key | Where | Meaning |
|---|---|---|
| `title_id` | title, **required** | The PlayFab title ID. Quote it if it's all digits: `"12345"`. |
| `description` | title | A note, shown by `titles`. |
| `host` | title or defaults | API address. `{title_id}` is filled in. Default `https://{title_id}.playfabapi.com`. |
| `cloudscripts` | title or defaults | CloudScript functions players may run through pfcli. |
| `player` | title or defaults | How the game creates, updates and reads players. |
| `redact` | title or defaults | Patterns for game credentials to hide in the output. |

A title's `cloudscripts` and `player` entries are combined with the ones under `defaults`
(the title wins; `name: null` removes a default). `redact` patterns from both are used.

### Several titles of the same game

Dev, stage and prod titles of one game usually share the same CloudScript and player flow.
Write it once and reuse it with YAML anchors: `&name` labels a block, `*name` reuses it.

```yaml
titles:
  GAME-DEV:
    title_id: ABCD2
    cloudscripts: &game_cloudscripts
      getPlayerState: { writes: false, parameter: { session: $session } }
    player: &game_player
      state: { steps: [ { cloudscript: getPlayerState } ] }
  GAME-PROD:
    title_id: ABCD1
    cloudscripts: *game_cloudscripts
    player: *game_player
```

Only reuse a block on titles whose live CloudScript really has those functions; check each
title's script in Game Manager first. (Shared settings for **every** title can also go under
`defaults`.)

### `cloudscripts`

```yaml
cloudscripts:
  getPlayerState:
    description: Read the player's saved state
    writes: false
    parameter:
      session: $session
```

| Key | Default | Meaning |
|---|---|---|
| `description` | empty | A note. |
| `writes` | `true` | `false` marks a function that only reads (it still runs with `--dry-run`). |
| `parameter` | empty | What the function receives, with [placeholders](placeholders.md). |

A plain list also works: `cloudscripts: [getPlayerState, savePlayerSettings]`.

### `player`

```yaml
player:
  create: { description: ..., steps: [ ... ] }
  update: { description: ..., steps: [ ... ] }
  state:  { description: ..., steps: [ ... ] }
```

Each step is one of:

| Step | Meaning |
|---|---|
| `cloudscript: NAME` and optional `parameter: {...}` | Run an allowed CloudScript function; `parameter` adds to or replaces the function's own. |
| `call: Family/Endpoint` and `body: {...}` | Call a PlayFab endpoint pfcli knows. `Client/...` runs as the player; `Server/...` and `Admin/...` use the title secret key. |

`state` may only contain steps that read. See
[CloudScript and player sequences](../guides/cloudscript-and-sequences.md) for a full example.

### `redact`

A list of regular expressions. Anything in the output that matches is replaced by
`<redacted>`. Use it for credentials your game returns (for example extra login keys).
Session tickets are always hidden; you don't need to list them.

## Secrets file

```yaml
titles:
  ABCD1: "secret-key-for-ABCD1"
  ABCD2: "secret-key-for-ABCD2"
```

- One line per title: its **title ID**, then its secret key in quotes.
- Keep it private: `chmod 600`. pfcli warns if others can read it.
- One secrets file can hold keys for titles used by several configs.
- Instead of the file, a key can come from an environment variable
  `PFCLI_SECRET_<TITLE_ID>` (handy in CI). The file wins if both exist.
