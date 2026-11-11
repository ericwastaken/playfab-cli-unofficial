"""Minimal PlayFab REST client for a title's secret key (Server and Admin APIs).

Every endpoint pfcli may call is registered in ALLOWED_ENDPOINTS with its API family and
whether it reads or writes. Anything not registered raises before a request is sent.
What a call may actually do on the title is decided by the credentials (the secret key),
not by pfcli.
"""
import json
import logging
import time
import urllib.error
import urllib.request

logger = logging.getLogger("pfcli")

READ, WRITE = "read", "write"

# "<API family>/<Endpoint>" -> READ | WRITE. Families follow PlayFab's REST API:
# Server and Admin use the title secret key; Client needs a player session (not supported
# by this client yet).
ALLOWED_ENDPOINTS = {
    "Server/GetLeaderboard": READ,
    "Server/GetTitleData": READ,
    "Server/GetPlayerProfile": READ,
    "Server/GetPlayerStatisticVersions": READ,
}

SECRET_KEY_FAMILIES = {"Server", "Admin"}


class PlayFabError(RuntimeError):
    pass


def endpoint_access(endpoint: str) -> str:
    """READ or WRITE for a registered endpoint; raises if it is not registered."""
    if endpoint not in ALLOWED_ENDPOINTS:
        raise PlayFabError(f"{endpoint} is not registered in ALLOWED_ENDPOINTS")
    return ALLOWED_ENDPOINTS[endpoint]


class TitleClient:
    """Calls a title's Server/Admin endpoints with its secret key."""

    def __init__(self, title: dict):
        """title: a resolved entry from Config.title()."""
        self.alias = title["alias"]
        self.title_id = title["title_id"]
        self.host = title["host"]
        self.key = title["key"]
        if not self.key:
            raise PlayFabError(f"no secret key for title {self.title_id} "
                               f"(add it to the secrets file, or set PFCLI_SECRET_{self.title_id.upper()})")

    def call(self, endpoint: str, body: dict, dry_run: bool = False) -> dict:
        """POST to "<Family>/<Endpoint>" and return the output envelope:
        {title, titleId, endpoint, request, response}, where `response` is PlayFab's own
        reply (success or error) untouched. With dry_run, a WRITE endpoint is not sent:
        the envelope has "dryRun": true and "response": null. Reads always run.
        Raises PlayFabError only when no PlayFab reply was received."""
        access = endpoint_access(endpoint)
        family = endpoint.split("/", 1)[0]
        if family not in SECRET_KEY_FAMILIES:
            raise PlayFabError(f"{endpoint}: the {family} API needs a player session, "
                               f"which TitleClient does not support")
        env = {"title": self.alias, "titleId": self.title_id, "endpoint": endpoint, "request": body}
        if access == WRITE and dry_run:
            logger.info("DRY RUN %s %s: not sent", self.alias, endpoint)
            return {**env, "dryRun": True, "response": None}
        env["response"] = self._post(endpoint, body)
        return env

    def _post(self, endpoint: str, body: dict) -> dict:
        req = urllib.request.Request(
            f"{self.host}/{endpoint}",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "X-SecretKey": self.key},
        )
        last = None
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                try:
                    last = json.load(e)
                except ValueError:
                    last = {"code": e.code, "status": e.reason, "error": "NonJsonResponse"}
                if e.code == 429 or e.code >= 500:
                    wait = 2 ** attempt
                    logger.warning("%s %s: HTTP %s, retrying in %ss", self.alias, endpoint, e.code, wait)
                    time.sleep(wait)
                    continue
                return last
            except (urllib.error.URLError, TimeoutError) as e:
                raise PlayFabError(f"{endpoint}: {e}")
        logger.warning("%s %s: gave up after 5 attempts", self.alias, endpoint)
        return last


def ok(envelope: dict) -> bool:
    """True when the envelope holds a successful PlayFab reply (or a dry run)."""
    if envelope.get("dryRun"):
        return True
    return (envelope.get("response") or {}).get("code") == 200


def error_text(envelope: dict) -> str:
    r = envelope.get("response") or {}
    return f"{r.get('code')} {r.get('error') or r.get('status')}: {r.get('errorMessage') or ''}".strip()
