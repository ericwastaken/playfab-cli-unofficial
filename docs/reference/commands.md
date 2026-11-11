# Commands

`pfcli [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]`. `ALIAS...` means one or more title names
from your config. Run any command with `--help` for its full details.

## Global options

Put these **before** the command name.

| Option | Meaning |
|---|---|
| `--config FILE` | Your config file. Default: `pfcli-config.yml` in the pfcli folder. |
| `--secrets FILE` | Your secrets file. Default: the one matching the config's name (`pfcli-config-acme.yml` → `pfcli-secrets-acme.yml`). |
| `--sessions FILE` | Saved player logins. Default: matching the config's name (`pfcli-sessions-acme.yml`). |
| `-o, --output-format NAME\|FILE` | Reshape the output (see [Shape the output](../guides/output-formats.md)). |
| `--raw` | Print only PlayFab's reply, without pfcli's labels. |
| `--log-level LEVEL` | How chatty the on-screen messages are: DEBUG, INFO, WARNING, ERROR. |

## Access tags

Every command is tagged in its help:

- **READ ONLY**: only reads.
- **READ WRITE**: can change data in PlayFab. Has `--dry-run`.
- **LOCAL WRITE**: changes only a pfcli file on your computer. Has `--dry-run`.

## Local

| Command | Access | What it does |
|---|---|---|
| `titles` | READ ONLY | Lists your titles, whether each key was found, allowed CloudScript functions and player sequences. |

## `server`: with the title secret key

| Command | Access | What it does |
|---|---|---|
| `server get-leaderboard ALIAS... -s STAT` | READ ONLY | Reads a leaderboard. `--max N` (default 100), `--start N`, `--version N` (a past version), `--pause S`. |
| `server get-title-data ALIAS... [-k KEY]...` | READ ONLY | Reads TitleData; no `-k` means all keys. |
| `server get-player-combined-info ALIAS... [-p ID]... [--input FILE\|-]` | READ ONLY | Reads players' details. `--id-column NAME`, `-r TEMPLATE`, `--var NAME=VALUE`, `--concurrency N`. |

## `client`: as a logged-in player

All need a saved login (`-u CUSTOM_ID`) except the login and create commands. See
[Act as a player](../guides/act-as-a-player.md).

| Command | Access | What it does |
|---|---|---|
| `client login-with-custom-id ALIAS... -u ID...` | READ WRITE | Logs players in and saves their logins. `--input FILE\|-`, `--create-account`, `--skip-create-steps`. |
| `client create-player ALIAS... -u ID... [--var NAME=VALUE]...` | READ WRITE | Creates players the game's way (`player.create`). |
| `client update-player ALIAS... -u ID... [--var NAME=VALUE]...` | READ WRITE | Updates players the game's way (`player.update`). |
| `client get-player-state ALIAS... -u ID...` | READ ONLY | Reads players the game's way (`player.state`). |
| `client execute-cloud-script ALIAS... -u ID... -f FUNCTION` | READ WRITE | Runs an allowed CloudScript function. `--var`, `--params JSON` (extra fields), `--revision N`, `--playstream-event`. |
| `client get-leaderboard ALIAS... -u ID... -s STAT` | READ ONLY | A leaderboard as the player sees it. Same options as the server version. |
| `client get-player-profile ALIAS... -u ID... [-p OTHER]...` | READ ONLY | The player's profile, or other players'. |
| `client get-user-data ALIAS... -u ID... [-p OTHER]... [-k KEY]...` | READ ONLY | Player data, own or others'. |
| `client get-account-info ALIAS... -u ID... [-p OTHER]...` | READ ONLY | Account info, own or others'. |
| `client get-title-data ALIAS... -u ID... [-k KEY]...` | READ ONLY | TitleData a game client can read. |
| `client get-catalog-items ALIAS... -u ID... [-c VERSION]` | READ ONLY | The item catalog as a player sees it. |
| `client get-player-combined-info ALIAS... -u ID... [-p OTHER]... [-r TEMPLATE]` | READ ONLY | Combined info as the player sees it. |
| `client update-user-title-display-name ALIAS... -u ID... -n NAME` | READ WRITE | Changes the display name directly (many titles block this; use your game's way instead). |
| `client sessions list [VALUE...]` | READ ONLY | Lists saved logins. `--title`, `--expired`. |
| `client sessions flush [VALUE...]` | LOCAL WRITE | Removes saved logins. `--title`, `--expired`, `--all`. |

## Exit status

- `0`: everything worked.
- `1`: something failed (a title was skipped, PlayFab returned an error, a CloudScript reported
  an error, a login was missing). Details are on screen; results that did arrive are still
  in the output.
