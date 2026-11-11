# Set up your titles

pfcli needs two small files, kept in the pfcli folder:

| File | What's in it | Secret? |
|---|---|---|
| **Config** `pfcli-config-<name>.yml` | Your titles: a short name for each, its title ID and its address | No |
| **Secrets** `pfcli-secrets-<name>.yml` | Each title's secret key | **Yes** |

`<name>` is any label you like, for example the studio or project: `pfcli-config-acme.yml`
and `pfcli-secrets-acme.yml`. Keeping one pair per project keeps projects apart.

## 1. Create the config

Copy the example and edit it:

```bash
cp pfcli-config.example.yml pfcli-config-acme.yml
```

A minimal config:

```yaml
titles:
  GAME-PROD:                 # a short name (alias) you'll type in commands
    title_id: ABCD1          # Game Manager > your title > Settings > General
    description: Our game, production
  GAME-DEV:
    title_id: ABCD2
    description: Our game, development
```

!!! tip "Titles on a dedicated cluster"
    Some titles live on their own PlayFab cluster with a different API address. If a command
    fails with `InvalidAPIEndpoint`, add that title's address:
    ```yaml
      GAME-PROD:
        title_id: ABCD1
        host: "https://{title_id}.your-cluster.playfabapi.com"
    ```

## 2. Create the secrets file

```bash
cp pfcli-secrets.example.yml pfcli-secrets-acme.yml
chmod 600 pfcli-secrets-acme.yml
```

Paste each title's secret key next to its **title ID**:

```yaml
titles:
  ABCD1: "your-secret-key-for-ABCD1"
  ABCD2: "your-secret-key-for-ABCD2"
```

To find a key: **Game Manager > your title > Settings (gear) > Title settings > Secret Keys**.
A dedicated key for pfcli is a good idea, so you can revoke it on its own.

!!! danger "A secret key is full access"
    A title secret key can read **and change** everything in that title. Keep the secrets file
    private (`chmod 600`), never share it, and never paste keys into chat or tickets. pfcli
    never prints keys.

## 3. Check your setup

```bash
pfcli --config pfcli-config-acme.yml -o titles-table titles
```

pfcli finds `pfcli-secrets-acme.yml` by itself, because its name matches the config. Every
title should show `set (file)`:

```text
alias      titleId  key         host                              description
GAME-PROD  ABCD1    set (file)  https://ABCD1.playfabapi.com      Our game, production
GAME-DEV   ABCD2    set (file)  https://ABCD2.playfabapi.com      Our game, development
```

`EMPTY` means pfcli didn't find a key for that title ID: check the secrets file.

Next: [Your first commands](first-commands.md).
