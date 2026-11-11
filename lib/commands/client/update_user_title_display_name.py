import click

from ...pfcommand import READ_WRITE, pf_command
from .common import SESSION_NOTES, custom_id_option, emit_checked, for_each_session


@pf_command("update-user-title-display-name", READ_WRITE, ("Client/UpdateUserTitleDisplayName",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@click.option("--display-name", "-n", required=True, help="New display name for the logged-in player.")
@click.pass_context
def update_user_title_display_name(ctx, aliases, custom_ids, display_name, dry_run):
    """Change the logged-in player's display name.

    READ WRITE: sends Client/UpdateUserTitleDisplayName for each session. Use --dry-run to
    see the requests first. PlayFab applies the title's name rules and may reject the name.
    """

    def action(client, s):
        envs, good = [], True
        for body in [{"DisplayName": display_name}]:
            env = client.call("Client/UpdateUserTitleDisplayName", body, s["sessionTicket"], dry_run=dry_run)
            env["customId"] = s["customId"]
            envs.append(env)
            good &= emit_checked(ctx, env, f"{client.alias} {s['customId']}")
        return good, envs

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
