# Several titles at once

Every command that talks to PlayFab accepts **one or more titles**. List them one after
another:

```bash
pfcli --config pfcli-config-acme.yml -o leaderboard-names \
  server get-leaderboard GAME-PROD GAME-DEV GAME-ASIA -s score --max 5000 > names.csv
```

## How it works

- **Each title uses its own settings**: its own address (even on different clusters) and its
  own secret key.
- **Titles run in the order you list them**, and their results go into the same output.
- **Every result says which title it came from** (`title` and `titleId`), so a format or
  `jq` can tell them apart. The built-in `leaderboard-names` format puts the title in the
  first column.
- **One failing title doesn't stop the others.** An unknown name, a missing key, or a PlayFab
  error is reported on screen, that title is skipped, and the rest still run. pfcli then
  exits with status 1, so scripts can tell something went wrong.
- Title names aren't case-sensitive: `game-prod` finds `GAME-PROD`.

## Split the results afterwards

```bash
pfcli --config pfcli-config-acme.yml -o leaderboard-entries \
  server get-leaderboard GAME-PROD GAME-DEV -s score --max 1000 \
  | jq -c 'select(.title == "GAME-DEV")' > dev.ndjson
```

`pfcli --config ... titles` lists the names your config defines.
