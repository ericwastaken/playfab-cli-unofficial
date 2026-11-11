import csv
import json
from pathlib import Path

import click

from ..config import ConfigError
from ..pfcommand import READ_ONLY, pf_command


@pf_command("names-report", READ_ONLY)
@click.argument("raw_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), default=None,
              help="Output folder. Default: the parent of RAW_DIR.")
@click.option("--include-defaults", is_flag=True,
              help="Keep names matching default_name_patterns in known-good-names.csv "
                   "(flagged default_name=yes) instead of dropping them.")
@click.pass_context
def names_report(ctx, raw_dir, out, include_defaults):
    """Build CSVs from leaderboard-names output (offline).

    Reads RAW_DIR/<ALIAS>-<board>.json and writes:

    \b
      leaderboard-names.csv   title, board, statistic, version, rank, display_name, default_name
      known-good-names.csv    title, display_name, boards, best_rank, default_name
                              (unique names per title; blanks removed; names matching the
                               title's default_name_patterns removed unless --include-defaults)
    """
    cfg = ctx.obj["config"]
    out = out or raw_dir.parent
    files = sorted(raw_dir.glob("*-*.json"))
    if not files:
        raise click.ClickException(f"No <ALIAS>-<board>.json files in {raw_dir}")
    all_rows, good, stats, patterns = [], {}, {}, {}
    for f in files:
        d = json.loads(f.read_text())
        alias = d["alias"]
        board = d["board"]
        if alias not in patterns:
            try:
                patterns[alias] = cfg.title(alias)["default_name_patterns"]
            except ConfigError:
                patterns[alias] = []
                click.echo(f"{alias}: not in config; no default-name filtering", err=True)
        s = stats.setdefault(alias, {"rows": 0, "blank": 0, "default": 0})
        for r in d["rows"]:
            name = (r["name"] or "").strip()
            is_default = bool(name) and any(p.search(name) for p in patterns[alias])
            all_rows.append([alias, board, d["statistic"], d["version"], r["rank"], name,
                             "yes" if is_default else "no"])
            s["rows"] += 1
            if not name:
                s["blank"] += 1
                continue
            if is_default:
                s["default"] += 1
                if not include_defaults:
                    continue
            g = good.setdefault((alias, name), {"boards": set(), "best_rank": r["rank"], "default": is_default})
            g["boards"].add(board)
            g["best_rank"] = min(g["best_rank"], r["rank"])

    lb = out / "leaderboard-names.csv"
    with lb.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["title", "board", "statistic", "version", "rank", "display_name", "default_name"])
        w.writerows(sorted(all_rows, key=lambda r: (r[0], r[1], r[4])))
    kg = out / "known-good-names.csv"
    with kg.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["title", "display_name", "boards", "best_rank", "default_name"])
        for (alias, name), g in sorted(good.items(), key=lambda kv: (kv[0][0], kv[1]["best_rank"])):
            w.writerow([alias, name, "+".join(sorted(g["boards"])), g["best_rank"], "yes" if g["default"] else "no"])

    summary = [{"title": a, **s, "known_good": sum(1 for k in good if k[0] == a),
                "defaults_included": include_defaults} for a, s in sorted(stats.items())]
    if ctx.obj["json_output"]:
        click.echo(json.dumps({"files": [str(lb), str(kg)], "titles": summary}, indent=2))
        return
    for s in summary:
        kept = "included" if include_defaults else "excluded"
        click.echo(f"{s['title']}: {s['rows']} leaderboard rows, {s['blank']} blank, "
                   f"{s['default']} default names ({kept}), {s['known_good']} unique names in known-good")
    click.echo(f"-> {lb}\n-> {kg}")
