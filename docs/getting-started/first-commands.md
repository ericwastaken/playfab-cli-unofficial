# Your first commands

All examples use the config from [Set up your titles](setup.md). Commands that talk to
PlayFab are grouped the way PlayFab groups its API:

- **`pfcli server ...`** uses the title's secret key (full access, like your backend).
- **`pfcli client ...`** acts as a player (see [Act as a player](../guides/act-as-a-player.md)).

## Read a leaderboard

```bash
pfcli --config pfcli-config-acme.yml server get-leaderboard GAME-PROD -s score --max 10
```

- `GAME-PROD` is the title's short name from your config.
- `-s score` is the statistic (leaderboard) name, exactly as in Game Manager. Names are
  case-sensitive.
- `--max 10` is how many ranks to fetch. pfcli pages through big boards for you (100 at a
  time), so `--max 5000` works too.

You get PlayFab's own reply as JSON, one line per page. That's great for `jq` or saving to a
file, but hard to read. Add an output format to make it friendly:

```bash
pfcli --config pfcli-config-acme.yml -o leaderboard-entries server get-leaderboard GAME-PROD -s score --max 10
```

```text
{"title": "GAME-PROD", "statistic": "score", "position": 0, "playFabId": "...", "name": "Ace", "value": 98123}
{"title": "GAME-PROD", "statistic": "score", "position": 1, "playFabId": "...", "name": "Bea", "value": 87011}
```

!!! note "Where options go"
    Options that apply to every command (`--config`, `-o`, `--raw`) go **before** the command
    name. Options for one command (`-s`, `--max`) go **after** it.

## Save to a file

pfcli prints results; your shell saves them:

```bash
pfcli --config pfcli-config-acme.yml -o leaderboard-names server get-leaderboard GAME-PROD -s score --max 5000 > names.csv
```

Messages and warnings go to the screen, not into the file, so `names.csv` contains only data.

## Read TitleData

```bash
pfcli --config pfcli-config-acme.yml server get-title-data GAME-PROD -k CurrentEvent
pfcli --config pfcli-config-acme.yml -o title-data-rows server get-title-data GAME-PROD
```

Leave out `-k` to read every key.

## See every command

```bash
pfcli --help
pfcli server --help
pfcli client --help
pfcli server get-leaderboard --help
```

Every command's help starts with **`[READ ONLY]`**, **`[READ WRITE]`** or **`[LOCAL WRITE]`**
so you always know whether it can change anything. See [Security](../safety.md).

## Where to go next

- [Several titles at once](../guides/several-titles.md)
- [Shape the output](../guides/output-formats.md)
- [Look up many players](../guides/bulk-players.md)
- [Act as a player](../guides/act-as-a-player.md)
