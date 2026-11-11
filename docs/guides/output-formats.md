# Shape the output

## What you get by default

pfcli prints **PlayFab's own reply**, one JSON line per call, wrapped in a few labels that say
where it came from:

```json
{"title": "GAME-PROD", "titleId": "ABCD1", "endpoint": "Server/GetLeaderboard",
 "at": "2026-01-31T12:00:00Z", "request": {"StatisticName": "score", ...},
 "response": {"code": 200, "status": "OK", "data": {"Leaderboard": [...]}}}
```

- Want **only** PlayFab's reply? Add `--raw`.
- Want a **file**? Add `> results.ndjson`.
- Want it **reshaped**? Use an output format with `-o`.

Only results go to the output; messages go to the screen. See
[Output records](../reference/output.md) for the details.

## Use a built-in format

pfcli comes with ready-made formats (built in, nothing to download). Pick one with
`-o NAME` (before the command name):

| Format | Gives you |
|---|---|
| `leaderboard-names` | CSV of unique display names per title, without blanks and default-looking names |
| `leaderboard-entries` | One JSON line per leaderboard entry: title, statistic, position, playFabId, name, value |
| `title-data-rows` | CSV of TitleData: time, title, key, value |
| `player-summary` | CSV per player from combined info: title, playFabId, displayName, created, lastLogin, error |
| `titles-table` | Your titles as a table |
| `sessions-table` | Saved player sessions as a table |
| `segments-table` | `get-all-segments` as a table: title, id, name, description |
| `catalog-items` | CSV of catalog items: title, itemId, itemClass, displayName, catalogVersion, prices |
| `data` | Just the `data` part of each PlayFab reply |

```bash
pfcli --config pfcli-config-acme.yml -o player-summary \
  server get-player-combined-info GAME-PROD -p 1234567890ABCDEF -r player-basics
```

## Make your own format

A format is a small YAML file in an `output-formats` folder inside your pfcli folder.
**Name your own formats `user-<something>.yml`** so they're easy to keep private. Easiest
start: copy a built-in one from
[pfcli's built-in formats](https://github.com/ericwastaken/playfab-cli-unofficial/tree/main/src/pfcli/builtin/output-formats):

```bash
mkdir -p output-formats
curl -fsSL https://raw.githubusercontent.com/ericwastaken/playfab-cli-unofficial/main/src/pfcli/builtin/output-formats/leaderboard-names.yml \
  -o output-formats/user-acme-names.yml
```

Then use it as `-o user-acme-names`.

```yaml
# output-formats/user-acme-names.yml
description: Real player names from our leaderboards
format: csv                        # ndjson, json, yaml, csv, tsv or text
rows: response.data.Leaderboard    # make one row per leaderboard entry
fields:                            # the columns you want
  title: title
  rank: row.Position
  name: row.DisplayName
drop_empty: [name]                 # skip rows with no name
exclude:                           # skip names that look auto-generated
  name: ['^player_?\d{5,}$', '^guest\d+$']
unique: [title, name]              # each name once per title (the best rank wins)
```

What the keys mean:

| Key | Meaning |
|---|---|
| `format` | `ndjson` (one JSON per line, the default), `json` or `yaml` (one list), `csv` or `tsv` (with a header row), `text` (tab-separated, no header) |
| `rows` | Where the list lives in each result. Each item becomes one output row, available as `row`. Leave it out for one row per result. |
| `fields` | Output columns: a name and where its value comes from. `title` and `request...` come from the labels; `row....` from the current item. Needed for csv, tsv and text. |
| `drop_empty` | Skip rows where these columns are empty |
| `exclude` | Skip rows where a column matches a pattern (regular expression; add `(?i)` to ignore case) |
| `unique` | Keep only the first row for each combination of these columns |
| `description` | A note for yourself |

The "where it comes from" parts use [JMESPath](https://jmespath.org/), a small query
language for JSON. Two extra helpers are available:

- `to_entries(...)` turns a map into rows of `key` and `value`, handy for TitleData and
  UserData: `rows: to_entries(response.data.Data)`.
- `from_json(...)` reads a value that is stored as JSON text, e.g.
  `level: from_json(row.value).level`.

!!! tip "Not sure what's in the reply?"
    Run the command without `-o` first and look at the JSON (or pipe it to `jq`). Then write
    the format.

If a format has a mistake (an unknown key, a bad expression), pfcli tells you before it
contacts PlayFab.
