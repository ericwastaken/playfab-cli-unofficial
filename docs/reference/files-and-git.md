# Files and Git

pfcli keeps **your** files private automatically. Git ignores them by name, so they can never
be committed by accident when your pfcli folder is the pfcli repository. If your pfcli folder
is in another repository, add the same patterns to its `.gitignore` (see
[Install](../install.md#3-make-a-pfcli-folder)).

| File | Private? |
|---|---|
| `pfcli-config-<name>.yml`, `pfcli-secrets-<name>.yml`, `pfcli-sessions-<name>.yml` | Yes |
| Any other `pfcli*.yml` / `pfcli*.yaml` (e.g. `pfcli-config.yml`) | Yes |
| `output-formats/user-*.yml`, `request-templates/user-*.yml` | Yes |
| `pfcli-exports/` (downloaded segment exports: player data) | Yes |
| `.env` files (pfcli doesn't use them; ignored just in case) | Yes |
| `pfcli-config.example.yml`, `pfcli-secrets.example.yml` (in pfcli's repository) | No: examples |
| Built-in formats and templates | Not in your folder: they ship inside pfcli |

!!! tip "Name your own formats and templates `user-...`"
    A format or template **without** the `user-` prefix is treated as part of pfcli. Keep
    anything about your project in `user-` files.

Check any file name:

```bash
git check-ignore -v output-formats/user-acme-names.yml
```
