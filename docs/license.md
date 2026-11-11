---
description: pfcli's license (MIT), the unofficial / trademark notice, third-party licenses, and how PlayFab's own terms apply.
---

# License

## The short version

pfcli is free and open source under the **MIT License**. You can use, copy, change and share
it, including at work and in commercial projects, as long as the copyright and license notice
stay with it. It comes with **no warranty**: you use it at your own risk.

!!! warning "Unofficial: not affiliated with Microsoft"
    pfcli is **not affiliated with, endorsed by, or supported by Microsoft, Azure PlayFab or
    PlayFab**. "PlayFab" and "Azure PlayFab" are trademarks of Microsoft, used here only to
    say what pfcli works with. pfcli acts with the keys and logins you give it, and you are
    responsible for what it does to your titles. See [Security](safety.md).

## Full license text

This is the repository's [`LICENSE`](https://github.com/ericwastaken/playfab-cli-unofficial/blob/main/LICENSE)
file, included here when the site is built:

```text
--8<-- "LICENSE"
```

The same license covers pfcli's code, this documentation, and the project artwork (the
banner and logo).

## Third-party software

pfcli and this site are built on these open-source projects, each under its own license:

| Used by | Project | License |
|---|---|---|
| pfcli | [Click](https://github.com/pallets/click) | BSD-3-Clause |
| pfcli | [JMESPath (jmespath.py)](https://github.com/jmespath/jmespath.py) | MIT |
| pfcli | [PyYAML](https://github.com/yaml/pyyaml) | MIT |
| This site | [MkDocs](https://github.com/mkdocs/mkdocs) | BSD-2-Clause |
| This site | [Material for MkDocs](https://github.com/squidfunk/mkdocs-material) | MIT |
| This site | Material Design Icons by [Pictogrammers](https://pictogrammers.com/) (bundled with Material for MkDocs) | Pictogrammers Free License (icons under Apache 2.0) |

uv installs these together with pfcli; their license files are included in each installed
package.

## PlayFab's own terms

pfcli calls PlayFab's public REST APIs. Your use of PlayFab, its APIs and your titles' data
is governed by **your own agreement with Microsoft**, not by pfcli's license. Check
Microsoft's terms for PlayFab, and your organization's policies, before using pfcli on a
title.
