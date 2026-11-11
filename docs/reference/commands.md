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
- **READ WRITE**: can change data in PlayFab. Has `--dry-run`. Writes on many players or
  several titles, and deletions, also need `--yes`.
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
| `server get-friends-list ALIAS... -p ID...` | READ ONLY | Read a player's friend list. |
| `server add-friend ALIAS... -p ID... [--friend-playfab-id VALUE] [--friend-username VALUE] [--friend-email VALUE] [--friend-display-name VALUE]` | **READ WRITE** | Add a friend to a player's friend list. Needs `--yes` above 10 targets or for several titles. |
| `server remove-friend ALIAS... -p ID... --friend-playfab-id VALUE` | **READ WRITE** | Remove a friend from a player's friend list. Needs `--yes` above 10 targets or for several titles. |
| `server update-avatar-url ALIAS... -p ID... --image-url VALUE` | **READ WRITE** | Set a player's avatar URL. Needs `--yes` above 10 targets or for several titles. |
| `server add-player-tag ALIAS... -p ID... --tag VALUE` | **READ WRITE** | Add a tag to players. Needs `--yes` above 10 targets or for several titles. |
| `server remove-player-tag ALIAS... -p ID... --tag VALUE` | **READ WRITE** | Remove a tag from players. Needs `--yes` above 10 targets or for several titles. |
| `server get-player-tags ALIAS... -p ID... [--namespace VALUE]` | READ ONLY | Read players' tags. |
| `server consume-item ALIAS... -p ID... --item-instance-id VALUE --count VALUE [--character-id VALUE]` | **READ WRITE** | Consume uses of an item instance in a player's inventory. Needs `--yes` above 10 targets or for several titles. |
| `server add-user-virtual-currency ALIAS... -p ID... --currency VALUE --amount VALUE` | **READ WRITE** | Add virtual currency to players. Needs `--yes` above 10 targets or for several titles. |
| `server subtract-user-virtual-currency ALIAS... -p ID... --currency VALUE --amount VALUE` | **READ WRITE** | Subtract virtual currency from players. Needs `--yes` above 10 targets or for several titles. |
| `server get-catalog-items ALIAS... [--catalog-version VALUE]` | READ ONLY | Read the (legacy) item catalog. |
| `server get-leaderboard-around-user ALIAS... -p ID... --statistic VALUE [--max VALUE] [--version VALUE]` | READ ONLY | Read leaderboard entries around a player. |
| `server get-user-account-info ALIAS... -p ID...` | READ ONLY | Read players' account info. |
| `server get-all-segments ALIAS...` | READ ONLY | List the title's player segments. |
| `server get-player-segments ALIAS... -p ID...` | READ ONLY | List the segments a player belongs to. |
| `server delete-player ALIAS... -p ID...` | **READ WRITE** | Delete players from this title (their title data). **Cannot be undone: always needs `--yes`.** |

## `admin`: with the title secret key

Same key as `server`; PlayFab's Admin API also covers account-level and title-management calls.

| Command | Access | What it does |
|---|---|---|
| `admin update-user-title-display-name ALIAS... -p ID... --display-name VALUE` | **READ WRITE** | Set players' display names (admin). Needs `--yes` above 10 targets or for several titles. |
| `admin add-player-tag ALIAS... -p ID... --tag VALUE` | **READ WRITE** | Add a tag to players. Needs `--yes` above 10 targets or for several titles. |
| `admin remove-player-tag ALIAS... -p ID... --tag VALUE` | **READ WRITE** | Remove a tag from players. Needs `--yes` above 10 targets or for several titles. |
| `admin get-player-tags ALIAS... -p ID... [--namespace VALUE]` | READ ONLY | Read players' tags. |
| `admin add-user-virtual-currency ALIAS... -p ID... --currency VALUE --amount VALUE` | **READ WRITE** | Add virtual currency to players. Needs `--yes` above 10 targets or for several titles. |
| `admin subtract-user-virtual-currency ALIAS... -p ID... --currency VALUE --amount VALUE` | **READ WRITE** | Subtract virtual currency from players. Needs `--yes` above 10 targets or for several titles. |
| `admin get-catalog-items ALIAS... [--catalog-version VALUE]` | READ ONLY | Read the (legacy) item catalog. |
| `admin get-user-account-info ALIAS... -p ID...` | READ ONLY | Read players' account info. |
| `admin get-all-segments ALIAS...` | READ ONLY | List the title's player segments. |
| `admin get-player-segments ALIAS... -p ID...` | READ ONLY | List the segments a player belongs to. |
| `admin export-players-in-segment ALIAS... --segment-id VALUE` | READ ONLY | Start an export of all players in a segment. |
| `admin get-segment-export ALIAS... --export-id VALUE` | READ ONLY | Read the status and download links of a segment export. |
| `admin delete-player ALIAS... -p ID...` | **READ WRITE** | Delete players from this title (their title data). **Cannot be undone: always needs `--yes`.** |
| `admin delete-master-player-account ALIAS... -p ID... [--metadata VALUE]` | **READ WRITE** | Permanently delete players' master accounts (all titles). **Cannot be undone: always needs `--yes`.** |

## `client`: as a logged-in player

All need a saved login (`-u CUSTOM_ID`) except the login and create commands. Many titles
block some of these for players (`403 NotAuthorizedByTitle`); that's the title's API policy. See
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
| `client get-friends-list ALIAS... -u ID...` | READ ONLY | Read the logged-in player's friend list. |
| `client add-friend ALIAS... -u ID... [--friend-playfab-id VALUE] [--friend-username VALUE] [--friend-email VALUE] [--friend-display-name VALUE]` | **READ WRITE** | Add a friend for the logged-in player. Needs `--yes` above 10 targets or for several titles. |
| `client remove-friend ALIAS... -u ID... --friend-playfab-id VALUE` | **READ WRITE** | Remove a friend for the logged-in player. Needs `--yes` above 10 targets or for several titles. |
| `client update-avatar-url ALIAS... -u ID... --image-url VALUE` | **READ WRITE** | Set the logged-in player's avatar URL. Needs `--yes` above 10 targets or for several titles. |
| `client get-player-tags ALIAS... -u ID... [-p OTHER]... [--namespace VALUE]` | READ ONLY | Read player tags as a logged-in player. |
| `client consume-item ALIAS... -u ID... --item-instance-id VALUE --count VALUE [--character-id VALUE]` | **READ WRITE** | Consume uses of an item the logged-in player owns. Needs `--yes` above 10 targets or for several titles. |
| `client add-user-virtual-currency ALIAS... -u ID... --currency VALUE --amount VALUE` | **READ WRITE** | Add virtual currency as the logged-in player. Needs `--yes` above 10 targets or for several titles. |
| `client subtract-user-virtual-currency ALIAS... -u ID... --currency VALUE --amount VALUE` | **READ WRITE** | Subtract virtual currency as the logged-in player. Needs `--yes` above 10 targets or for several titles. |
| `client get-leaderboard-around-player ALIAS... -u ID... [-p OTHER]... --statistic VALUE [--max VALUE] [--version VALUE]` | READ ONLY | Read leaderboard entries around a player, as a logged-in player. |
| `client get-player-segments ALIAS... -u ID...` | READ ONLY | List the segments the logged-in player belongs to. |
| `client sessions list [VALUE...]` | READ ONLY | Lists saved logins. `--title`, `--expired`. |
| `client sessions flush [VALUE...]` | LOCAL WRITE | Removes saved logins. `--title`, `--expired`, `--all`. |

## Exit status

- `0`: everything worked.
- `1`: something failed (a title was skipped, PlayFab returned an error, a CloudScript reported
  an error, a login was missing). Details are on screen; results that did arrive are still
  in the output.
