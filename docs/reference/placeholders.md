# Placeholders and --var

Request templates, CloudScript parameters and player sequences are written in YAML. Wherever
a value is **exactly** one of these, pfcli fills it in:

| Placeholder | Filled from |
|---|---|
| `$.column` | The current input row (`--input` file or pipe) |
| `$session` | The player's login ticket (hidden in the output) |
| `$playFabId` | The logged-in player's PlayFab ID |
| `$customId` | The logged-in player's custom ID |
| `$titleId` | The title's ID |
| `$NAME` | `--var NAME=VALUE` on the command line. Required: if missing, pfcli stops before sending anything. |
| `$NAME?` | The same, but optional: if you don't give it, the field is left out. |

```yaml
parameter:
  id: $playFabId
  session: $session
  name: $name?        # only sent if you pass --var name=...
```

```bash
pfcli --config pfcli-config-acme.yml client update-player GAME-DEV -u tester-01 --var name=Tester
```

- `--var` can be repeated: `--var name=Tester --var color=blue`.
- You can't set the reserved names (`session`, `playFabId`, `customId`, `titleId`) with
  `--var`.
- `pfcli --config ... titles` shows which placeholders each CloudScript function takes.

!!! warning "Quote optional placeholders inside one-line maps and lists"
    YAML treats a bare `?` inside `{ ... }` or `[ ... ]` as syntax. Write
    `{ name: "$name?" }` there. On its own line (`name: $name?`) no quotes are needed.

## Options, templates or config?

pfcli keeps a simple rule: **you type values; files hold structure.**

- Small, simple requests take **options**: `-s score`, `-k CurrentEvent`, `-n NewName`.
- Big or nested requests use a **request template** (`-r`).
- Things only your game defines (CloudScript parameters, player sequences) live in your
  **config**.
- Values for all of them come from `--var`, input rows, or the player's login.
