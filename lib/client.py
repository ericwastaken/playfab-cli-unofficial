"""Minimal PlayFab REST clients.

- TitleClient calls Server and Admin endpoints with the title's secret key.
- PlayerClient calls Client endpoints as a player: LoginWithCustomID needs no auth;
  every other Client call uses a session ticket saved by a login (see lib/sessions.py).

Every endpoint pfcli may call is registered in ALLOWED_ENDPOINTS with its API family and
whether it reads or writes. Anything not registered raises before a request is sent.
What a call may actually do on the title is decided by the credentials, not by pfcli.
"""
import json
import logging
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger("pfcli")

READ, WRITE = "read", "write"

# "<API family>/<Endpoint>" -> READ | WRITE, named as in PlayFab's REST API.
ALLOWED_ENDPOINTS = {
    "Server/GetLeaderboard": READ,
    "Server/GetTitleData": READ,
    "Server/GetPlayerCombinedInfo": READ,
    "Server/GetPlayerProfile": READ,
    "Server/GetPlayerStatisticVersions": READ,
    "Server/UpdateUserData": WRITE,
    # Login can create a player (CreateAccount) and fires the title's login automations.
    "Client/LoginWithCustomID": WRITE,
    "Client/GetLeaderboard": READ,
    "Client/GetPlayerProfile": READ,
    "Client/GetUserData": READ,
    "Client/GetAccountInfo": READ,
    "Client/GetPlayerCombinedInfo": READ,
    "Client/UpdateUserTitleDisplayName": WRITE,
    # Runs title code that can do anything; only functions allowed in the config are sent.
    "Client/ExecuteCloudScript": WRITE,
}

SECRET_KEY_FAMILIES = {"Server", "Admin"}
SESSION_FAMILIES = {"Client"}
NO_AUTH_ENDPOINTS = {"Client/LoginWithCustomID"}

# PlayFab errors that mean the session ticket is no longer valid.
SESSION_ERRORS = {"NotAuthenticated", "InvalidSessionTicket", "SessionTicketExpired", "NotAuthorized"}


class PlayFabError(RuntimeError):
    pass


def endpoint_access(endpoint: str) -> str:
    """READ or WRITE for a registered endpoint; raises if it is not registered."""
    if endpoint not in ALLOWED_ENDPOINTS:
        raise PlayFabError(f"{endpoint} is not registered in ALLOWED_ENDPOINTS")
    return ALLOWED_ENDPOINTS[endpoint]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _Base:
    families: set = set()

    def __init__(self, title: dict):
        """title: a resolved entry from Config.title()."""
        self.alias = title["alias"]
        self.title_id = title["title_id"]
        self.host = title["host"]
        # Title-specific credentials to hide in every output record (config `redact`).
        self.redact = [re.compile(p) for p in title.get("redact") or []]

    def protect(self, env: dict, *secrets: str) -> dict:
        """Copy of a record with the given secrets (e.g. the session ticket) and anything
        matching the title's `redact` patterns replaced by <redacted>, in request and
        response alike (some titles echo tickets or login keys back in their replies)."""
        return _scrub(env, [s for s in secrets if s], self.redact)

    def _envelope(self, endpoint: str, body: dict) -> dict:
        return {"title": self.alias, "titleId": self.title_id, "endpoint": endpoint,
                "at": utc_now(), "request": body}

    def _check(self, endpoint: str) -> str:
        access = endpoint_access(endpoint)
        family = endpoint.split("/", 1)[0]
        if family not in self.families:
            raise PlayFabError(f"{endpoint}: {type(self).__name__} does not call the {family} API")
        return access

    def _send(self, endpoint: str, body: dict, headers: dict, access: str, dry_run: bool) -> dict:
        env = self._envelope(endpoint, body)
        if access == WRITE and dry_run:
            logger.info("DRY RUN %s %s: not sent", self.alias, endpoint)
            return {**env, "dryRun": True, "response": None}
        env["response"] = self._post(endpoint, body, headers)
        return self.protect(env)

    def _post(self, endpoint: str, body: dict, headers: dict) -> dict:
        req = urllib.request.Request(
            f"{self.host}/{endpoint}",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", **headers},
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


class TitleClient(_Base):
    """Calls a title's Server/Admin endpoints with its secret key."""
    families = SECRET_KEY_FAMILIES

    def __init__(self, title: dict):
        super().__init__(title)
        self.key = title["key"]
        if not self.key:
            raise PlayFabError(f"no secret key for title {self.title_id} "
                               f"(add it to the secrets file, or set PFCLI_SECRET_{self.title_id.upper()})")

    def call(self, endpoint: str, body: dict, dry_run: bool = False) -> dict:
        """POST to "<Family>/<Endpoint>" and return the output envelope:
        {title, titleId, endpoint, at, request, response}, where `response` is PlayFab's own
        reply (success or error) untouched. With dry_run, a WRITE endpoint is not sent:
        the envelope has "dryRun": true and "response": null. Reads always run.
        Raises PlayFabError only when no PlayFab reply was received."""
        access = self._check(endpoint)
        return self._send(endpoint, body, {"X-SecretKey": self.key}, access, dry_run)


class PlayerClient(_Base):
    """Calls a title's Client endpoints as a player. No secret key is used."""
    families = SESSION_FAMILIES

    def call(self, endpoint: str, body: dict, session_ticket: str | None = None,
             dry_run: bool = False, treat_as_read: bool = False) -> dict:
        """Like TitleClient.call. Every Client endpoint except LoginWithCustomID needs the
        session_ticket of a logged-in player (sent as X-Authorization). The ticket is
        redacted wherever it appears in the echoed request. treat_as_read sends a WRITE
        endpoint even under dry_run (for CloudScript functions the config marks
        writes: false)."""
        access = self._check(endpoint)
        headers = {}
        if endpoint not in NO_AUTH_ENDPOINTS:
            if not session_ticket:
                raise PlayFabError(f"{endpoint} needs a player session")
            headers["X-Authorization"] = session_ticket
        env = self._send(endpoint, body, headers, READ if treat_as_read else access, dry_run)
        return self.protect(env, session_ticket)


def _scrub(obj, secrets, patterns=()):
    """Copy of obj with every occurrence of the secrets (strings) and of the patterns
    (compiled regexes) inside string values replaced by <redacted>."""
    if isinstance(secrets, str):
        secrets = [secrets]
    if isinstance(obj, dict):
        return {k: _scrub(v, secrets, patterns) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(v, secrets, patterns) for v in obj]
    if isinstance(obj, str):
        for s in secrets:
            if s and s in obj:
                obj = obj.replace(s, "<redacted>")
        for p in patterns:
            obj = p.sub("<redacted>", obj)
    return obj


def ok(envelope: dict) -> bool:
    """True when the envelope holds a successful PlayFab reply (or a dry run)."""
    if envelope.get("dryRun"):
        return True
    return (envelope.get("response") or {}).get("code") == 200


def session_expired(envelope: dict) -> bool:
    r = envelope.get("response") or {}
    return r.get("code") == 401 or r.get("error") in SESSION_ERRORS


def error_text(envelope: dict) -> str:
    r = envelope.get("response") or {}
    return f"{r.get('code')} {r.get('error') or r.get('status')}: {r.get('errorMessage') or ''}".strip()
