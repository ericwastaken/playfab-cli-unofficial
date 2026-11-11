---
description: pfcli is agent friendly. Point your AI coding agent at SKILL.md to use pfcli safely, or AGENT.md to work on pfcli's code.
---

# Use pfcli with an AI agent

pfcli is **agent friendly**. AI coding agents (Claude Code, Codex, Cursor and similar) can run
it for you, because it's a plain command-line tool with predictable output and clear safety
labels. The repository includes instruction files written for agents, so they know how to
use pfcli without guessing.

## Which file to point your agent at

<div class="grid cards" markdown>

-   :material-robot: **To use pfcli: `SKILL.md`**

    ---

    How to run pfcli on your behalf: commands, output, config, and strict **safety rules**
    (never read your secrets, dry-run and ask before any write, prefer dev titles, clean up
    sessions).

    [View SKILL.md on GitHub](https://github.com/ericwastaken/playfab-cli-unofficial/blob/main/SKILL.md){ .md-button .md-button--primary }

-   :material-code-braces: **To change pfcli's code: `AGENT.md`**

    ---

    For agents working on pfcli itself: house rules, architecture traps, how to add
    commands, and what must never be committed.

    [View AGENT.md on GitHub](https://github.com/ericwastaken/playfab-cli-unofficial/blob/main/AGENT.md){ .md-button }

</div>

## Quick start: just tell your agent

If pfcli is already cloned, open your agent in the pfcli folder and say:

> Read `SKILL.md` in this folder and follow it. Then, using my config `pfcli-config-acme.yml`,
> list my titles and show the top 20 of the `score` leaderboard on GAME-DEV as a table.

The agent finds everything else from there.

## Let an agent set you up

New to pfcli? Ask your agent:

> Read `SKILL.md` and set up pfcli for my PlayFab titles.

It switches to **bootstrap mode**: it asks for a project label and your titles one at a time
(and tells you where to find each title ID in Game Manager), shows the `pfcli init` command
it will run, creates the files, and then asks **you** to paste your secret keys into the
secrets file in your own editor. It never asks for your keys and never opens that file.
Finally it runs `pfcli titles --verify` to prove everything works.

## Install the skill

Some agents load reusable **skills** from a skills folder. To make pfcli's skill available in
a project:

```bash
mkdir -p .agents/skills/pfcli
curl --fail --location \
  https://raw.githubusercontent.com/ericwastaken/playfab-cli-unofficial/main/SKILL.md \
  --output .agents/skills/pfcli/SKILL.md
```

Or for every project, in your user account:

```bash
mkdir -p ~/.agents/skills/pfcli
curl --fail --location \
  https://raw.githubusercontent.com/ericwastaken/playfab-cli-unofficial/main/SKILL.md \
  --output ~/.agents/skills/pfcli/SKILL.md
```

!!! note "Use your agent's skills folder"
    Some agents use their own folder instead of `.agents/skills`. Keep the `pfcli/SKILL.md`
    layout inside whatever folder your agent documents. Restart the agent (or ask it to reload
    skills) after installing. Run the same command again to update it.

## Keep your agent safe

`SKILL.md` tells agents to follow these rules, but you stay in charge:

- **Don't give an agent your secret keys.** pfcli reads them from your secrets file; the
  agent never needs to see them, and `SKILL.md` forbids opening that file.
- **Approve writes one at a time.** Agents are told to show a `--dry-run` and wait for your
  yes before any READ WRITE command.
- **Point it at a development title** while you get comfortable.
- Read the [Security](safety.md) page: everything there applies to agents too.
