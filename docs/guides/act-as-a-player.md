# Act as a player

The `pfcli client ...` commands use PlayFab's **Client API**: the same calls a game makes for a
signed-in player. They use **no secret key**, only the player's login. That makes them perfect
for checking what your title shows to players, and for testing with test accounts.

## Two steps: log in, then act

**1. Log in once** per player and title. pfcli saves the login (a "session"):

```bash
pfcli --config pfcli-config-acme.yml client login-with-custom-id GAME-DEV -u tester-01
```

`-u` (`--custom-id`) is the player's custom ID: the login ID your game uses.

**2. Run any client command as that player**, with the same `-u`:

```bash
pfcli --config pfcli-config-acme.yml client get-account-info   GAME-DEV -u tester-01
pfcli --config pfcli-config-acme.yml client get-player-profile GAME-DEV -u tester-01 -p FEDCBA0987654321
pfcli --config pfcli-config-acme.yml client get-leaderboard    GAME-DEV -u tester-01 -s score
```

Client commands never log in by themselves. If there's no saved login, or it has expired,
they tell you the exact login command to run.

`-p` (`--playfab-id`) reads **another** player, which shows what one player can find out about
others. Without `-p`, you read the logged-in player.

## New test players

Logging in with a custom ID that doesn't exist yet fails with `AccountNotFound`, so you can't
create players by accident. To create one on purpose:

- If your config describes how your game creates players, use
  `client create-player` (see [CloudScript and player sequences](cloudscript-and-sequences.md)).
- Otherwise: `client login-with-custom-id GAME-DEV -u tester-01 --create-account`.

!!! warning "Logging in is a write"
    A login can create a player (with `--create-account`) and can trigger the title's own
    automations or CloudScript. That's why login is tagged **READ WRITE**. Try `--dry-run`
    first to see the request without sending it. Use a development title.

## Your saved logins

Logins are saved next to your config, in `pfcli-sessions-acme.yml` (private, ignored by Git).
A login lasts about 24 hours.

```bash
pfcli --config pfcli-config-acme.yml -o sessions-table client sessions list
```

To remove logins, say which ones: any value that identifies them works (custom ID, PlayFab ID,
or title):

```bash
pfcli --config pfcli-config-acme.yml client sessions flush tester-01
pfcli --config pfcli-config-acme.yml client sessions flush --title GAME-DEV
pfcli --config pfcli-config-acme.yml client sessions flush --expired
pfcli --config pfcli-config-acme.yml client sessions flush --all --dry-run
```

Removing a login only stops pfcli from using it; PlayFab keeps it valid until it expires.

## Several players or titles

`-u` can be repeated, and you can list several titles. Each player needs its own login on
each title.

```bash
pfcli --config pfcli-config-acme.yml client login-with-custom-id GAME-DEV -u tester-01 -u tester-02
pfcli --config pfcli-config-acme.yml -o data client get-account-info GAME-DEV -u tester-01 -u tester-02
```

## "NotAuthorizedByTitle"

Many titles have an **API policy** that blocks some Client calls for players (for example,
changing the display name directly, or reading other players' data). pfcli shows PlayFab's
reply, prints the error on screen and exits with status 1. That's useful information: it's
exactly what a game client (or someone imitating one) would get.
