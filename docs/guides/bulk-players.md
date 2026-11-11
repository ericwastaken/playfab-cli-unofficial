# Look up many players

`server get-player-combined-info` fetches players' details (profile, data, statistics and
more) using the title's secret key.

## A few players

```bash
pfcli --config pfcli-config-acme.yml -o player-summary \
  server get-player-combined-info GAME-PROD -p 1234567890ABCDEF -p FEDCBA0987654321
```

## A list of players from a file

Give pfcli a CSV with a header row:

```text
PlayFabId,batch
1234567890ABCDEF,march
FEDCBA0987654321,march
```

```bash
pfcli --config pfcli-config-acme.yml -o player-summary \
  server get-player-combined-info GAME-PROD --input players.csv > summary.csv
```

- If the ID column has another name, say which: `--id-column playerId`.
- `--concurrency 10` runs more requests at once (default 5).
- Each result includes the input row, so a format can show your own columns next to
  PlayFab's.

## Chain pfcli commands

pfcli can read its own output. Take the top 100 of a leaderboard and look each player up:

```bash
pfcli --config pfcli-config-acme.yml -o leaderboard-entries \
  server get-leaderboard GAME-PROD -s score --max 100 \
| pfcli --config pfcli-config-acme.yml -o player-summary \
  server get-player-combined-info GAME-PROD --input - --id-column playFabId -r player-basics
```

`--input -` means "read from the previous command".

## Choose what to fetch: request templates

By default pfcli asks for each player's profile with display name. To ask for more, use a
**request template**: the PlayFab request written as YAML.

The built-in `player-basics` template asks for profile, account info, user data and
statistics:

```bash
pfcli --config pfcli-config-acme.yml server get-player-combined-info GAME-PROD -p 1234567890ABCDEF -r player-basics
```

To make your own, copy it to `request-templates/user-<something>.yml` (private, ignored by
Git) and edit it:

```yaml
# request-templates/user-acme-progress.yml
PlayFabId: $.PlayFabId          # filled from each input row
InfoRequestParameters:
  GetUserData: true
  UserDataKeys:
    - progress
    - $extraKey?
  GetPlayerStatistics: true
  PlayerStatisticNames: [score]
```

```bash
pfcli --config pfcli-config-acme.yml server get-player-combined-info GAME-PROD \
  --input players.csv -r user-acme-progress --var extraKey=settings
```

`$.PlayFabId` takes a value from the input row; `$extraKey?` takes a value from `--var`
(and is left out if you don't give one). See [Placeholders and --var](../reference/placeholders.md).
The [PlayFab REST reference](https://learn.microsoft.com/rest/api/playfab/) lists every
field a request can have.
