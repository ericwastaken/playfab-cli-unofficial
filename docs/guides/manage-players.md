# Manage players (Server and Admin)

With a title's **secret key**, pfcli can do what your game's backend does: look players up,
change their names and avatars, manage friends and tags, give or take virtual currency,
consume items, and, carefully, delete players. These commands use PlayFab's **Server** and
**Admin** APIs, so they work even when your title blocks the same actions for players.

!!! danger "These change real players"
    A secret key has full access. Start on a **development title** with **test players**, and
    run every write with `--dry-run` first. See [Security](../safety.md).

## Look players up

```bash
pfcli --config pfcli-config-acme.yml server get-user-account-info GAME-DEV -p 1234567890ABCDEF
pfcli --config pfcli-config-acme.yml server get-player-tags GAME-DEV -p 1234567890ABCDEF
pfcli --config pfcli-config-acme.yml server get-friends-list GAME-DEV -p 1234567890ABCDEF
pfcli --config pfcli-config-acme.yml server get-player-segments GAME-DEV -p 1234567890ABCDEF
pfcli --config pfcli-config-acme.yml server get-leaderboard-around-user GAME-DEV -p 1234567890ABCDEF -s score --max 5
```

Every player command takes several players (`-p` repeated) or a list (`--input players.csv`,
or `--input -` from a pipe), and several titles at once.

## Change players

```bash
pfcli --config pfcli-config-acme.yml admin update-user-title-display-name GAME-DEV -p 1234567890ABCDEF -n Tester --dry-run
pfcli --config pfcli-config-acme.yml server update-avatar-url GAME-DEV -p 1234567890ABCDEF --image-url https://example.com/a.png
pfcli --config pfcli-config-acme.yml server add-player-tag GAME-DEV -p 1234567890ABCDEF -t beta-tester
pfcli --config pfcli-config-acme.yml server add-friend GAME-DEV -p 1234567890ABCDEF --friend-playfab-id FEDCBA0987654321
pfcli --config pfcli-config-acme.yml server add-user-virtual-currency GAME-DEV -p 1234567890ABCDEF -c GD -a 100
pfcli --config pfcli-config-acme.yml server consume-item GAME-DEV -p 1234567890ABCDEF --item-instance-id 0123ABCD -n 1
```

!!! note "Admin name changes skip your game's name checks"
    `admin update-user-title-display-name` sets the name directly. Any moderation your game
    does (for example in CloudScript) does not run.

## The `--yes` guard

pfcli stops a write before it starts when it could affect a lot at once:

- **More than 10 players, or several titles:** pfcli refuses until you add `--yes`.
- **Deletions** (`server delete-player`, `admin delete-player`,
  `admin delete-master-player-account`): **always** need `--yes`, because they can't be undone.

The safe routine: run with `--dry-run`, read what would be sent, then run again with `--yes`.

```bash
pfcli --config pfcli-config-acme.yml server add-player-tag GAME-DEV --input testers.csv -t beta --dry-run
pfcli --config pfcli-config-acme.yml server add-player-tag GAME-DEV --input testers.csv -t beta --yes
```

## Delete players

| Command | Removes |
|---|---|
| `server delete-player` / `admin delete-player` | The player's data **in this title** |
| `admin delete-master-player-account` | The player's **master account in every title** of the studio |

```bash
pfcli --config pfcli-config-acme.yml admin delete-master-player-account GAME-DEV -p 1234567890ABCDEF --dry-run
pfcli --config pfcli-config-acme.yml admin delete-master-player-account GAME-DEV -p 1234567890ABCDEF --yes
```

## Catalog and segments

```bash
pfcli --config pfcli-config-acme.yml -o catalog-items server get-catalog-items GAME-DEV
pfcli --config pfcli-config-acme.yml -o segments-table admin get-all-segments GAME-DEV
```

## Export the players in a segment

PlayFab exports a segment **in the background**: it takes a snapshot of every matching
player profile and prepares it as files. That can take a while for big segments, so pfcli
lets you wait for it and download the result in one go:

```bash
# Find the segment's ID
pfcli --config pfcli-config-acme.yml -o segments-table admin get-all-segments GAME-DEV

# Start the export, wait until it's ready, and download the files
pfcli --config pfcli-config-acme.yml admin export-players-in-segment GAME-DEV \
  --segment-id 1A2B3C4D5E6F7A8B --download
```

- Progress (`Pending`, `Processing`, ...) is shown on screen while it waits. `--timeout`
  (default 900 seconds) and `--poll` (default 10) control the waiting.
- The files land in `pfcli-exports/GAME-DEV-<EXPORT_ID>/` in your pfcli folder (keep it
  private), or in `--dir`. pfcli never overwrites files.
- You can also do it in steps:

  ```bash
  pfcli --config pfcli-config-acme.yml admin export-players-in-segment GAME-DEV --segment-id 1A2B3C4D5E6F7A8B
  pfcli --config pfcli-config-acme.yml admin get-segment-export GAME-DEV --export-id <EXPORT_ID>
  pfcli --config pfcli-config-acme.yml admin download-segment-export GAME-DEV --export-id <EXPORT_ID>
  ```

What you get: an index file (`exportcomplete.txt`, one download link per line) and one or
more **TSV** files (tab-separated, one row per player, with a header row). Columns include
`PlayerId`, `DisplayName`, `Created`, `LastLogin`, `Tags`, `PlayerStatistics`,
`VirtualCurrencyBalances`, `LinkedAccounts`, `ContactEmailAddresses` and last-login
location (country, city, latitude/longitude). Open them in a spreadsheet, or process them
with your own tools.

!!! danger "Exports are player data"
    The files contain player profiles, including **email addresses and location**. Keep
    them private, share them only as your privacy
    rules allow, and delete them when you're done. The download links PlayFab returns work
    on their own (no key needed), so pfcli never shows them in full: their access part
    appears as `<redacted>`.

## The same actions as a player

Many of these also exist under `client` (friends, avatar, consume item, virtual currency,
tags, segments, leaderboard around the player). Those run as a logged-in player and are often
blocked by the title's API policy, which is exactly what they help you check. See
[Act as a player](act-as-a-player.md).
