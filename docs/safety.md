---
description: How to use pfcli securely - keys, player logins (sessions), flushing them, what to do if something leaks, and handling output.
---

# Security

!!! warning "Unofficial tool, your responsibility"
    pfcli is **not affiliated with Microsoft, Azure PlayFab or PlayFab** and comes with no
    warranty. It can do anything the keys and logins you give it allow, including changing
    live data for real players. **Use it at your own risk.**

pfcli works with real credentials for real games. This page explains what those credentials
can do, where pfcli keeps them, and the habits that keep you, your players and your titles
safe.

## Do and don't

<div class="grid cards" markdown>

-   :material-check-circle: **Do**

    ---

    - Start on a **development title** with **test players**.
    - Run every **READ WRITE** command with **`--dry-run`** first, then confirm big or
      destructive ones with **`--yes`**.
    - Use a **dedicated secret key** for pfcli, so you can revoke it on its own.
    - Keep secrets and session files **private** (`chmod 600`).
    - **Flush player sessions** when you're done testing.
    - Keep your own formats and templates in **`user-...` files**.
    - Treat pfcli's **output as player data**: store and share it carefully.

-   :material-close-circle: **Don't**

    ---

    - Don't paste **secret keys or session tickets** into chat, tickets, email or docs.
    - Don't **commit or share** `pfcli-secrets-*`, `pfcli-sessions-*` or `user-*` files.
    - Don't run write commands against **production** until you've tried them on dev.
    - Don't point a title's `host` at **anything but PlayFab**.
    - Don't put **real title IDs, keys or player data** in files that aren't private.
    - Don't assume a **flushed** session is dead (see below).
    - Don't log in as **someone else's** player without permission.

</div>

## Know what each credential can do

| Credential | Where pfcli keeps it | What someone holding it can do |
|---|---|---|
| **Title secret key** | Your secrets file `pfcli-secrets-<name>.yml` | **Everything** on that title through the Server and Admin APIs: read and change any player, data, inventory or setting. |
| **Player session** (login ticket) | Your sessions file `pfcli-sessions-<name>.yml` | Act **as that player** on that title (whatever the title lets players do), for about 24 hours. |
| **Game-specific login keys** (some games return them) | Not kept | Log in as that player. Add a pattern under `redact` so pfcli hides them. |

pfcli's safety features ([below](#what-pfcli-does-for-you)) prevent **mistakes**. They are
not a lock: anyone who has a key or ticket can use it with any other tool. **Protect the
credentials themselves.**

## Secret keys

- **Create a key just for pfcli**: Game Manager > your title > Settings > Secret Keys. If it
  ever leaks, you can disable that one key without breaking your game's backend.
- **Keep the secrets file private**: `chmod 600 pfcli-secrets-<name>.yml`. pfcli warns you
  if other users on your computer can read it.
- **Never print, paste or share it.** pfcli itself never prints keys: `titles` only says
  `set` or `EMPTY`.
- **In CI**, provide keys as masked secret variables named `PFCLI_SECRET_<TITLE_ID>` instead
  of a file.

### If a secret key leaks

1. In Game Manager, **disable or delete that key** right away (Settings > Secret Keys).
2. Create a new key and put it in your secrets file.
3. Review recent activity on the title for anything you didn't do.

## Player sessions (logins)

The `client` commands act as a player. You log in once, and pfcli saves that login, a
**session**, so later commands can use it. See [Act as a player](guides/act-as-a-player.md).

**What's saved:** for each title and player: the login ticket, the player's PlayFab ID, the
custom ID and when you logged in. It's stored in `pfcli-sessions-<name>.yml` next to your
config, readable only by you (`chmod 600`), and ignored by Git.

**How long it lasts:** about **24 hours**. After that, client commands refuse to use it and
tell you to log in again. If PlayFab rejects a session sooner, pfcli marks it expired.

**Where tickets never appear:** in pfcli's output. Login tickets are replaced by
`<redacted>` everywhere, even when a game sends one back in its reply.

### See your saved sessions

```bash
pfcli --config pfcli-config-acme.yml -o sessions-table client sessions list
pfcli --config pfcli-config-acme.yml -o sessions-table client sessions list --expired
```

### Flush (remove) sessions

Remove sessions you no longer need, especially at the end of a testing session. Say which
ones with **any value that identifies them**: a custom ID, a PlayFab ID, a title name or a
title ID.

```bash
# one player, on every title
pfcli --config pfcli-config-acme.yml client sessions flush tester-01

# everything on one title
pfcli --config pfcli-config-acme.yml client sessions flush --title GAME-DEV

# only expired sessions
pfcli --config pfcli-config-acme.yml client sessions flush --expired

# everything (preview first, then for real)
pfcli --config pfcli-config-acme.yml client sessions flush --all --dry-run
pfcli --config pfcli-config-acme.yml client sessions flush --all
```

`flush` asks for a selector or `--all`, so a bare `flush` can't wipe everything by accident.

!!! danger "Flushing does not log the player out of PlayFab"
    Flushing only deletes pfcli's copy of the session. PlayFab has no "log out" for a
    session ticket, so the ticket **stays valid until it expires** (about 24 hours). That's
    why the sessions file must stay private.

### If a sessions file leaks

1. **Flush** the sessions in it (`client sessions flush --all`) so pfcli stops using them.
2. Assume the leaked tickets **work for up to 24 hours**. Anyone holding them can act as
   those players.
3. If those were **test players**, consider removing them from the title. If they were
   **real players**, treat it as a security incident under your team's process.

## Writes, dry runs and retries

- Every command is tagged **READ ONLY**, **READ WRITE** (changes data in PlayFab) or
  **LOCAL WRITE** (changes only a pfcli file). The tag is at the top of each command's
  `--help`.
- **`--dry-run`** shows exactly what a write would send, and sends nothing. Reads still run.
- **pfcli never repeats a write after a server error.** If PlayFab answers a write with a
  server error, the change **may or may not** have happened; pfcli stops and tells you to
  check before running it again. (Rate-limit replies, which mean nothing happened, are
  retried automatically.)
- A **login is a write**: it can create a player (with `--create-account`) and can trigger
  the title's own login automations.

## Output is player data

pfcli prints what PlayFab returns: **display names, PlayFab IDs, user data, inventory**.
That can be personal data.

- Save output only where your team's privacy rules allow, and delete it when you're done.
- Use an output format to keep **only the fields you need** (see
  [Shape the output](guides/output-formats.md)).
- Before sharing output, check it doesn't contain anything private. Login tickets are
  always hidden; add your game's own secrets to `redact`.

## Your files and Git

All of these are private automatically (Git ignores them): `pfcli-config-*`,
`pfcli-secrets-*`, `pfcli-sessions-*`, and `user-*` formats and templates. Anything else in
the pfcli folder could be committed, so keep project details in those files. See
[Files and Git](reference/files-and-git.md).

## What pfcli does for you

- **Labels every command** READ ONLY / READ WRITE / LOCAL WRITE.
- **Rehearses writes** with `--dry-run`.
- **Asks for `--yes`** before writes on more than 10 players, on several titles, and before
  any deletion.
- **Only sends PlayFab calls it knows**, each marked as a read or a write.
- **Only runs CloudScript you allow** for each title.
- **Keeps reads as reads**: `get-player-state` refuses steps that write.
- **Won't create players by accident**: an unknown login ID fails unless you ask to create
  it.
- **Hides credentials**: secret keys and login tickets never appear in output; your
  `redact` patterns hide the rest.
- **Doesn't repeat writes** after a server error.
- **Keeps your files private** and warns about readable secrets or sessions files.
- **Talks only to PlayFab**: no telemetry.

## License

pfcli's code is under the **MIT License** and comes with no warranty. See [License](license.md).

## Report a security problem

Found a vulnerability in pfcli? Please don't open a public issue: use GitHub's
[private vulnerability reporting](https://github.com/ericwastaken/playfab-cli-unofficial/security/advisories/new).
