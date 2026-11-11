# CloudScript and player sequences

Many games don't let players call PlayFab directly for everything. Instead they call the
game's own **CloudScript** functions, and some create or update players through several calls
in a row. pfcli lets you describe that in your config, then run it with one command.

!!! note "This part of the config is yours"
    Function names, their parameters and your game's sequences are specific to your game.
    Keep them in your own `pfcli-config-<name>.yml` (private, ignored by Git). The names below
    (`savePlayerSettings`, `getPlayerState`) are just examples.

## 1. Allow CloudScript functions

pfcli only runs functions you list for a title:

```yaml
titles:
  GAME-DEV:
    title_id: ABCD2
    cloudscripts:
      getPlayerState:
        description: Read the player's saved state
        writes: false                 # only reads
        parameter:
          session: $session
      savePlayerSettings:
        description: Save the player's settings
        parameter:
          id: $playFabId
          session: $session
          name: $name?
          color: $color?
```

- `writes: false` marks a function that only reads. Everything else counts as a write
  (the default), so `--dry-run` won't send it.
- `parameter` is what the function receives. The `$...` words are filled in for you:
  `$session` and `$playFabId` come from the player's login; `$name?` and `$color?` come from
  `--var name=...` and are left out if you don't give them. See
  [Placeholders and --var](../reference/placeholders.md).

Run one:

```bash
pfcli --config pfcli-config-acme.yml client execute-cloud-script GAME-DEV -u tester-01 \
  -f savePlayerSettings --var color=blue --dry-run
```

`pfcli --config ... titles` lists each title's allowed functions and the `$...` values each
one takes. A function that isn't listed is refused before anything is sent.

## 2. Describe how your game handles players

Under `player`, describe up to three sequences. Each is a list of steps, run in order:

| Sequence | Command | What it's for |
|---|---|---|
| `create` | `client create-player` | Create a new player the game's way. pfcli first logs in with "create account", then runs the steps. |
| `update` | `client update-player` | Change a player the game's way. |
| `state` | `client get-player-state` | Read a player the game's way. Every step must only read. |

A step is either **a CloudScript function** from your allowed list, or **a PlayFab call**
with its body. This example uses both:

```yaml
    player:
      create:                         # PlayFab calls
        steps:
          - call: Server/UpdateUserData           # uses the title secret key
            body:
              PlayFabId: $playFabId
              Data:
                profileVersion: "1"
                color: $color?
          - call: Client/UpdateUserTitleDisplayName   # runs as the player
            body:
              DisplayName: $name
      update:                         # the game's CloudScript
        steps:
          - cloudscript: savePlayerSettings
      state:                          # PlayFab calls that only read
        steps:
          - call: Client/GetPlayerProfile
            body:
              PlayFabId: $playFabId
              ProfileConstraints: { ShowDisplayName: true }
          - call: Client/GetUserData
            body:
              Keys: [profileVersion, color]
```

Some games use one CloudScript function for both create and update; that works too:
just list the same function under both.

## 3. Run them

```bash
pfcli --config pfcli-config-acme.yml client create-player GAME-DEV -u tester-01 --var name=Tester --var color=blue
pfcli --config pfcli-config-acme.yml client update-player GAME-DEV -u tester-01 --var color=green
pfcli --config pfcli-config-acme.yml client get-player-state GAME-DEV -u tester-01
```

- Steps stop at the first failure, and pfcli says which step failed.
- `create-player` leaves an existing player alone and tells you to use `update-player`.
- `--dry-run` shows every step without sending anything (on `create-player` and
  `update-player`).
- Once a title has a `create` sequence, `login-with-custom-id --create-account` refuses and
  points you to `create-player`, so you don't end up with half-made players.

## Errors inside CloudScript

CloudScript reports its own errors inside a normal-looking reply. pfcli checks for them: a
script error, or a result that looks like an error (for example a rejected name), is printed
on screen and the command exits with status 1. The full reply is still in the output.

## Keep game credentials out of the output

Some games send login keys or tickets back in their replies. pfcli always hides the
player's session ticket. For anything else your game treats as a password, add a pattern
under `redact` and pfcli replaces matches with `<redacted>` everywhere:

```yaml
    redact:
      - 'LOGINKEY-[0-9a-f]+'
```
