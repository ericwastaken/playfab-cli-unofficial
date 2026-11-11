# Files and Git

pfcli keeps **your** files private automatically. Git ignores them by name, so they can never
be committed by accident, even if you work inside the pfcli folder.

| File | Private? |
|---|---|
| `pfcli-config-<name>.yml`, `pfcli-secrets-<name>.yml`, `pfcli-sessions-<name>.yml` | Yes |
| Any other `pfcli*.yml` / `pfcli*.yaml` (e.g. `pfcli-config.yml`) | Yes |
| `output-formats/user-*.yml`, `request-templates/user-*.yml` | Yes |
| `.env` files (pfcli doesn't use them; ignored just in case) | Yes |
| `pfcli-config.example.yml`, `pfcli-secrets.example.yml` | No: examples that ship with pfcli |
| Other files in `output-formats/` and `request-templates/` | No: built-in, ship with pfcli |

!!! tip "Name your own formats and templates `user-...`"
    A format or template **without** the `user-` prefix is treated as part of pfcli. Keep
    anything about your project in `user-` files.

Check any file name:

```bash
git check-ignore -v output-formats/user-acme-names.yml
```
