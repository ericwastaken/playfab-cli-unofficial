# Troubleshooting

??? question "`Missing pfcli-config.yml`"
    pfcli didn't find a config. Pass yours: `--config pfcli-config-acme.yml`, or create one
    from `pfcli-config.example.yml` ([Set up your titles](getting-started/setup.md)).

??? question "`No titles defined`"
    A new config has no titles yet. Add one: `pfcli init acme --add-title GAME-DEV=ABCD2`
    (or edit the file).

??? question "`titles --verify` says the secret key was rejected"
    The key is wrong, disabled, or pasted next to the wrong title ID. Create a fresh key in
    Game Manager (Settings > Title settings > Secret Keys), paste it in the secrets file, and
    run `--verify` again.

??? question "`key EMPTY` in `titles`, or `no secret key for title ...`"
    pfcli didn't find that title's key. Check that the secrets file's name matches the config
    (`pfcli-config-acme.yml` ↔ `pfcli-secrets-acme.yml`), that it lists the **title ID** (not
    the alias), and that the key is in quotes. Player (`client`) commands don't need a key.

??? question "`InvalidAPIEndpoint`"
    The title is on a dedicated PlayFab cluster. Add its address to the title in your config:
    `host: "https://{title_id}.your-cluster.playfabapi.com"`.

??? question "A leaderboard comes back empty"
    PlayFab returns an empty board for a statistic that doesn't exist. Statistic names are
    case-sensitive: check the exact name in Game Manager. pfcli warns about this on screen.

??? question "`No such option`"
    Global options (`--config`, `-o`, `--raw`) go **before** the command; command options
    (`-s`, `-u`, `-r`) go **after** it.

??? question "`no saved session for custom ID ...` or `session ... has expired`"
    Client commands need a login first, and logins last about 24 hours. Run the
    `client login-with-custom-id` command pfcli shows you.

??? question "`AccountNotFound` when logging in"
    No player has that custom ID. Check the ID, or create the player on purpose
    (`client create-player`, or `--create-account`).

??? question "`403 NotAuthorizedByTitle`"
    The title's API policy blocks that call for players. That's the title's setting, not a
    pfcli problem. Your game may offer another way (often a CloudScript function).

??? question "`CloudScript function '...' is not allowed`"
    List the function under the title's `cloudscripts` in your config. `pfcli titles` shows
    what's allowed.

??? question "`no value for $name`"
    The request uses a placeholder you didn't fill. Add `--var name=VALUE`. See
    [Placeholders and --var](reference/placeholders.md).

??? question "`function returned an error` or `CloudScript error`"
    The game's CloudScript reported a problem (for example a rejected name, or missing player
    data). The full reply is in the output; look at its `response.data`.

??? question "A YAML error mentioning `?`"
    Quote optional placeholders inside one-line `{ }` or `[ ]`: `{ name: "$name?" }`.

??? question "pfcli stopped starting after I moved its folder"
    Delete the `.venv` folder and run `uv sync`.
