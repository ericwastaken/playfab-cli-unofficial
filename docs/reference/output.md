# Output records

## Results and messages are separate

- **Results** go to standard output: pipe them (`| jq`) or save them (`> file`).
- **Messages** (progress, warnings, errors) go to the screen (standard error), so they never
  end up in your file. To save them too: `2> messages.log`.

## Default: one JSON line per PlayFab call

```json
{"title": "GAME-PROD", "titleId": "ABCD1", "endpoint": "Server/GetLeaderboard",
 "at": "2026-01-31T12:00:00Z",
 "request": {"StatisticName": "score", "StartPosition": 0, "MaxResultsCount": 100},
 "response": {"code": 200, "status": "OK", "data": {"Leaderboard": [ ... ], "Version": 3}}}
```

| Label | Meaning |
|---|---|
| `title`, `titleId` | Which title the call was for |
| `endpoint` | The PlayFab call, e.g. `Server/GetLeaderboard` |
| `at` | When it ran (UTC) |
| `request` | What pfcli sent (credentials hidden) |
| `response` | PlayFab's reply, unchanged, including errors |
| `input` | The input row, for commands that read `--input` |
| `customId` | Which player's login made the call (client commands) |
| `sequence`, `step` | Which player sequence and step (create/update/state commands) |
| `dryRun` | `true` when `--dry-run` skipped sending; `response` is then `null` |

- A command that makes several calls (pages, titles, players) prints several lines.
- `--raw` prints only `response`.
- `titles` and `client sessions ...` print one line per title or saved login.
- Credentials never appear: session tickets and anything matching your `redact` patterns
  show as `<redacted>`.
