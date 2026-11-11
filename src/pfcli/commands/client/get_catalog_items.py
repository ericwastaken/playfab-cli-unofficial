import click

from ...pfcommand import READ_ONLY, pf_command
from .common import SESSION_NOTES, custom_id_option, emit_checked, for_each_session


@pf_command("get-catalog-items", READ_ONLY, ("Client/GetCatalogItems",), notes=SESSION_NOTES)
@click.argument("aliases", nargs=-1, required=True)
@custom_id_option
@click.option("--catalog-version", "-c", default=None,
              help="Catalog version to read. Default: the title's primary catalog.")
@click.pass_context
def get_catalog_items(ctx, aliases, custom_ids, catalog_version):
    """Read the (legacy) item catalog as a logged-in player sees it.

    One output record per title and session, holding PlayFab's GetCatalogItems response
    (response.data.Catalog is the list of items).
    """
    body = {"CatalogVersion": catalog_version} if catalog_version else {}

    def action(client, s):
        env = client.call("Client/GetCatalogItems", body, s["sessionTicket"])
        env["customId"] = s["customId"]
        return emit_checked(ctx, env, f"{client.alias} {s['customId']}"), [env]

    ctx.exit(0 if for_each_session(ctx, aliases, custom_ids, action) else 1)
