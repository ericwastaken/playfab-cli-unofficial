"""Table-driven commands for simple PlayFab endpoints.

Many PlayFab calls are a flat request (a player plus a few fields). Instead of one
near-identical module per call, each is described by an EndpointSpec and built by
build_command(). Commands with real logic (paging, templates, sessions, sequences) keep
their own modules. Every built command follows the house rules: named after the endpoint,
several titles per run, records emitted through the client (credentials scrubbed),
READ WRITE commands get --dry-run, and risky writes need --yes.

Scopes:
  player   Server/Admin: one call per player (-p ID..., or --input rows) per title.
  title    Server/Admin: one call per title (no player).
  session  Client: one call per saved session (-u CUSTOM_ID...) per title.
  session_target  Client: like session, plus optional -p OTHER players (default: self).
"""
from dataclasses import dataclass, field

import click

from ..client import PlayFabError, TitleClient, WRITE, ALLOWED_ENDPOINTS, error_text, ok
from ..config import ConfigError
from ..inputs import InputError, gather_rows
from ..pfcommand import READ_ONLY, READ_WRITE, pf_command

BULK_LIMIT = 10  # writes on more targets than this (or on several titles) need --yes


@dataclass
class Field:
    flags: tuple            # click option flags, e.g. ("--tag", "-t")
    key: str                # request body key, e.g. "TagName"
    help: str
    type: type = str
    required: bool = False
    default: object = None


@dataclass
class EndpointSpec:
    endpoint: str           # "Family/Name"
    scope: str              # player | title | session | session_target
    summary: str            # first help line
    details: str = ""
    fields: list = field(default_factory=list)
    fixed: dict = field(default_factory=dict)     # always-sent body fields
    guard: str | None = None                      # None | "bulk" | "always"
    one_of: tuple = ()      # body keys of which at least one is required

    @property
    def family(self) -> str:
        return self.endpoint.split("/", 1)[0]

    @property
    def name(self) -> str:
        n = self.endpoint.split("/", 1)[1]
        out = ""
        for i, ch in enumerate(n):
            if ch.isupper() and i and (not n[i - 1].isupper() or (i + 1 < len(n) and n[i + 1].islower())):
                out += "-"
            out += ch.lower()
        return out


def _body(spec: EndpointSpec, values: dict) -> dict:
    body = dict(spec.fixed)
    for f in spec.fields:
        v = values.get(f.key)
        if v not in (None, "", ()):
            body[f.key] = v
    return body


def _check_one_of(spec, body):
    if spec.one_of and not any(k in body for k in spec.one_of):
        names = " / ".join(f.flags[0] for f in spec.fields if f.key in spec.one_of)
        raise click.UsageError(f"give at least one of {names}")


def _guard(spec, n_targets: int, n_titles: int, yes: bool, dry_run: bool):
    if not spec.guard or dry_run or yes:
        return
    if spec.guard == "always":
        raise click.UsageError(f"{spec.endpoint} cannot be undone: review with --dry-run, then add --yes")
    if n_targets > BULK_LIMIT or n_titles > 1:
        raise click.UsageError(f"this would call {spec.endpoint} {n_targets} time(s) on {n_titles} title(s): "
                               f"review with --dry-run, then add --yes")


def build_command(spec: EndpointSpec):
    access = READ_WRITE if ALLOWED_ENDPOINTS[spec.endpoint] == WRITE else READ_ONLY
    notes = ""
    if spec.scope.startswith("session"):
        from .client.common import SESSION_NOTES
        notes = SESSION_NOTES
    if spec.guard == "always":
        notes = "\b\nGuard: this cannot be undone. It needs --yes (try --dry-run first).\n" + notes
    elif spec.guard == "bulk":
        notes = (f"\b\nGuard: more than {BULK_LIMIT} targets, or several titles, need --yes "
                 f"(try --dry-run first).\n" + notes)

    def run(ctx, aliases, playfab_ids=(), input_source=None, id_column=None, custom_ids=(), yes=False,
            dry_run=False, **opts):
        app = ctx.obj
        values = {f.key: opts.get(f.flags[0].lstrip("-").replace("-", "_")) for f in spec.fields}
        base = _body(spec, values)
        _check_one_of(spec, base)
        emit = app.emitter.emit
        failed = False

        if spec.scope in ("player", "title"):
            rows = [{}]
            if spec.scope == "player":
                try:
                    rows = gather_rows(playfab_ids, "PlayFabId", input_source, id_column)
                except InputError as e:
                    raise click.ClickException(str(e))
                if not rows:
                    raise click.UsageError("give at least one --playfab-id or an --input with rows")
            _guard(spec, len(rows) * len(aliases), len(aliases), yes, dry_run)
            for alias in aliases:
                try:
                    client = TitleClient(app.config.title(alias))
                except (ConfigError, PlayFabError) as e:
                    click.echo(f"{alias}: {e}; skipped", err=True)
                    failed = True
                    continue
                for row in rows:
                    body = {**base, **({"PlayFabId": row["PlayFabId"]} if spec.scope == "player" else {})}
                    try:
                        env = client.call(spec.endpoint, body, dry_run=dry_run)
                    except PlayFabError as e:
                        click.echo(f"{client.alias}: {e}", err=True)
                        failed = True
                        continue
                    if input_source:
                        env["input"] = row
                    emit(env)
                    if not ok(env):
                        who = f" {row.get('PlayFabId')}" if spec.scope == "player" else ""
                        click.echo(f"{client.alias}{who}: {error_text(env)}", err=True)
                        failed = True
            ctx.exit(1 if failed else 0)

        # Client scopes: one call per saved session (per target player for session_target).
        from .client.common import emit_checked, for_each_session
        _guard(spec, len(custom_ids) * len(aliases), len(aliases), yes, dry_run)

        def action(client, s):
            envs, good = [], True
            targets = (list(playfab_ids) or [s["playFabId"]]) if spec.scope == "session_target" else [None]
            for t in targets:
                body = {**base, **({"PlayFabId": t} if t else {})}
                env = client.call(spec.endpoint, body, s["sessionTicket"], dry_run=dry_run)
                env["customId"] = s["customId"]
                envs.append(env)
                good &= emit_checked(ctx, env, f"{client.alias} {s['customId']}")
            return good, envs

        ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)

    run.__doc__ = f"{spec.summary}\n\n{spec.details}".strip()
    f = click.pass_context(run)
    for fl in reversed(spec.fields):
        f = click.option(*fl.flags, fl.flags[0].lstrip("-").replace("-", "_"), type=fl.type,
                         required=fl.required, default=fl.default,
                         show_default=fl.default is not None, help=fl.help)(f)
    if spec.guard:
        f = click.option("--yes", is_flag=True, help="Confirm the write (see Guard below).")(f)
    if spec.scope == "player":
        f = click.option("--id-column", metavar="NAME", help="Input column holding the PlayFab ID.")(f)
        f = click.option("--input", "-i", "input_source", metavar="FILE|-",
                         help="More players: CSV with a header, or NDJSON; '-' reads stdin.")(f)
        f = click.option("--playfab-id", "-p", "playfab_ids", multiple=True, help="Player's PlayFab ID (repeatable).")(f)
    elif spec.scope.startswith("session"):
        if spec.scope == "session_target":
            f = click.option("--playfab-id", "-p", "playfab_ids", multiple=True,
                             help="Player to read (repeatable). Default: the logged-in player.")(f)
        f = click.option("--custom-id", "-u", "custom_ids", multiple=True, required=True,
                         help="Custom ID of a logged-in player (repeatable); picks the saved session.")(f)
    f = click.argument("aliases", nargs=-1, required=True)(f)
    f.__name__ = spec.name.replace("-", "_")
    return pf_command(spec.name, access, (spec.endpoint,), notes=notes)(f)


# ---------------------------------------------------------------------------------------
P = Field
FRIEND_FIELDS = [
    P(("--friend-playfab-id",), "FriendPlayFabId", "Friend's PlayFab ID."),
    P(("--friend-username",), "FriendUsername", "Friend's PlayFab username."),
    P(("--friend-email",), "FriendEmail", "Friend's email address."),
    P(("--friend-display-name",), "FriendTitleDisplayName", "Friend's display name in this title."),
]
FRIEND_ONE_OF = ("FriendPlayFabId", "FriendUsername", "FriendEmail", "FriendTitleDisplayName")
TAG = P(("--tag", "-t"), "TagName", "Tag name.", required=True)
NAMESPACE = P(("--namespace",), "Namespace", "Only tags in this namespace.")
VC = [P(("--currency", "-c"), "VirtualCurrency", "Virtual currency code (e.g. GD).", required=True),
      P(("--amount", "-a"), "Amount", "Amount (positive).", type=click.IntRange(min=1), required=True)]
CONSUME = [P(("--item-instance-id",), "ItemInstanceId", "Item instance to consume.", required=True),
           P(("--count", "-n"), "ConsumeCount", "Uses to consume.", type=click.IntRange(min=1), required=True),
           P(("--character-id",), "CharacterId", "Character that owns the item (if any).")]
CATALOG = [P(("--catalog-version",), "CatalogVersion", "Catalog version. Default: the primary catalog.")]
AROUND = [P(("--statistic", "-s"), "StatisticName", "Statistic (legacy leaderboard) name.", required=True),
          P(("--max",), "MaxResultsCount", "Entries around the player.", type=click.IntRange(1, 100), default=10),
          P(("--version",), "Version", "Statistic version. Default: current.", type=click.IntRange(min=0))]
SHOW_NAME = {"ProfileConstraints": {"ShowDisplayName": True}}

SPECS = [
    # ---- Server (title secret key) ----
    EndpointSpec("Server/GetFriendsList", "player", "Read a player's friend list.", fixed=SHOW_NAME),
    EndpointSpec("Server/AddFriend", "player", "Add a friend to a player's friend list.",
                 fields=FRIEND_FIELDS, one_of=FRIEND_ONE_OF, guard="bulk"),
    EndpointSpec("Server/RemoveFriend", "player", "Remove a friend from a player's friend list.",
                 fields=[P(("--friend-playfab-id",), "FriendPlayFabId", "Friend's PlayFab ID.", required=True)],
                 guard="bulk"),
    EndpointSpec("Server/UpdateAvatarUrl", "player", "Set a player's avatar URL.",
                 fields=[P(("--image-url",), "ImageUrl", "Avatar image URL.", required=True)], guard="bulk"),
    EndpointSpec("Server/AddPlayerTag", "player", "Add a tag to players.", fields=[TAG], guard="bulk"),
    EndpointSpec("Server/RemovePlayerTag", "player", "Remove a tag from players.", fields=[TAG], guard="bulk"),
    EndpointSpec("Server/GetPlayerTags", "player", "Read players' tags.", fields=[NAMESPACE]),
    EndpointSpec("Server/ConsumeItem", "player", "Consume uses of an item instance in a player's inventory.",
                 fields=CONSUME, guard="bulk"),
    EndpointSpec("Server/AddUserVirtualCurrency", "player", "Add virtual currency to players.", fields=VC,
                 guard="bulk"),
    EndpointSpec("Server/SubtractUserVirtualCurrency", "player", "Subtract virtual currency from players.",
                 fields=VC, guard="bulk"),
    EndpointSpec("Server/GetCatalogItems", "title", "Read the (legacy) item catalog.", fields=CATALOG),
    EndpointSpec("Server/GetLeaderboardAroundUser", "player", "Read leaderboard entries around a player.",
                 fields=AROUND, fixed=SHOW_NAME),
    EndpointSpec("Server/GetUserAccountInfo", "player", "Read players' account info."),
    EndpointSpec("Server/GetAllSegments", "title", "List the title's player segments."),
    EndpointSpec("Server/GetPlayerSegments", "player", "List the segments a player belongs to."),
    EndpointSpec("Server/DeletePlayer", "player", "Delete players from this title (their title data).",
                 details="Removes the player's data for this title. Use admin delete-master-player-account to "
                         "remove the master account across all titles.", guard="always"),
    # ---- Admin (title secret key) ----
    EndpointSpec("Admin/UpdateUserTitleDisplayName", "player", "Set players' display names (admin).",
                 details="Bypasses client-side name checks: the title's own moderation does not run.",
                 fields=[P(("--display-name", "-n"), "DisplayName", "New display name.", required=True)],
                 guard="bulk"),
    EndpointSpec("Admin/AddPlayerTag", "player", "Add a tag to players.", fields=[TAG], guard="bulk"),
    EndpointSpec("Admin/RemovePlayerTag", "player", "Remove a tag from players.", fields=[TAG], guard="bulk"),
    EndpointSpec("Admin/GetPlayerTags", "player", "Read players' tags.", fields=[NAMESPACE]),
    EndpointSpec("Admin/AddUserVirtualCurrency", "player", "Add virtual currency to players.", fields=VC,
                 guard="bulk"),
    EndpointSpec("Admin/SubtractUserVirtualCurrency", "player", "Subtract virtual currency from players.",
                 fields=VC, guard="bulk"),
    EndpointSpec("Admin/GetCatalogItems", "title", "Read the (legacy) item catalog.", fields=CATALOG),
    EndpointSpec("Admin/GetUserAccountInfo", "player", "Read players' account info."),
    EndpointSpec("Admin/GetAllSegments", "title", "List the title's player segments."),
    EndpointSpec("Admin/GetPlayerSegments", "player", "List the segments a player belongs to."),
    EndpointSpec("Admin/ExportPlayersInSegment", "title", "Start an export of all players in a segment.",
                 details="Starts an export job and returns its ExportId; read the result with "
                         "admin get-segment-export.",
                 fields=[P(("--segment-id",), "SegmentId", "Segment ID (from get-all-segments).", required=True)]),
    EndpointSpec("Admin/GetSegmentExport", "title", "Read the status and download links of a segment export.",
                 fields=[P(("--export-id",), "ExportId", "Export ID from export-players-in-segment.",
                           required=True)]),
    EndpointSpec("Admin/DeletePlayer", "player", "Delete players from this title (their title data).",
                 details="Use admin delete-master-player-account to remove the master account.", guard="always"),
    EndpointSpec("Admin/DeleteMasterPlayerAccount", "player",
                 "Permanently delete players' master accounts (all titles).",
                 details="Deletes the master player account and its data across every title of the studio. "
                         "This cannot be undone.",
                 fields=[P(("--metadata",), "MetaData", "Free text stored with the deletion request.")],
                 guard="always"),
    # ---- Client (as a logged-in player) ----
    EndpointSpec("Client/GetFriendsList", "session", "Read the logged-in player's friend list.", fixed=SHOW_NAME),
    EndpointSpec("Client/AddFriend", "session", "Add a friend for the logged-in player.",
                 fields=FRIEND_FIELDS, one_of=FRIEND_ONE_OF, guard="bulk"),
    EndpointSpec("Client/RemoveFriend", "session", "Remove a friend for the logged-in player.",
                 fields=[P(("--friend-playfab-id",), "FriendPlayFabId", "Friend's PlayFab ID.", required=True)],
                 guard="bulk"),
    EndpointSpec("Client/UpdateAvatarUrl", "session", "Set the logged-in player's avatar URL.",
                 fields=[P(("--image-url",), "ImageUrl", "Avatar image URL.", required=True)], guard="bulk"),
    EndpointSpec("Client/GetPlayerTags", "session_target", "Read player tags as a logged-in player.",
                 fields=[NAMESPACE]),
    EndpointSpec("Client/ConsumeItem", "session", "Consume uses of an item the logged-in player owns.",
                 fields=CONSUME, guard="bulk"),
    EndpointSpec("Client/AddUserVirtualCurrency", "session", "Add virtual currency as the logged-in player.",
                 details="Most titles disable this for clients (title setting).", fields=VC, guard="bulk"),
    EndpointSpec("Client/SubtractUserVirtualCurrency", "session",
                 "Subtract virtual currency as the logged-in player.", fields=VC, guard="bulk"),
    EndpointSpec("Client/GetLeaderboardAroundPlayer", "session_target",
                 "Read leaderboard entries around a player, as a logged-in player.", fields=AROUND, fixed=SHOW_NAME),
    EndpointSpec("Client/GetPlayerSegments", "session", "List the segments the logged-in player belongs to."),
]


def commands_for(family: str):
    return [build_command(s) for s in SPECS if s.family == family]
