"""Minimal PlayFab Server API client.

Only endpoints on the allow list (ALLOWED_READS, currently all reads) can be called.
Anything else raises before a request is sent, so nothing reaches a title by accident.
"""
import json
import logging
import time
import urllib.error
import urllib.request

logger = logging.getLogger("pfcli")

ALLOWED_READS = {"GetLeaderboard", "GetTitleData", "GetPlayerProfile", "GetPlayerStatisticVersions"}


class PlayFabError(RuntimeError):
    pass


class PlayFabServer:
    def __init__(self, title: dict):
        """title: a resolved entry from Config.title()."""
        self.alias = title["alias"]
        self.title_id = title["title_id"]
        self.host = title["host"]
        self.key = title["key"]
        if not self.key:
            raise PlayFabError(f"no secret key for title {self.title_id} "
                               f"(add it to the secrets file, or set PFCLI_SECRET_{self.title_id.upper()})")

    def call(self, api: str, body: dict) -> dict:
        if api not in ALLOWED_READS:
            raise PlayFabError(f"Server/{api} is not on the allow list (ALLOWED_READS)")
        req = urllib.request.Request(
            f"{self.host}/Server/{api}",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "X-SecretKey": self.key},
        )
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.load(r)["data"]
            except urllib.error.HTTPError as e:
                data = json.load(e)
                if e.code == 429 or e.code >= 500:
                    wait = 2 ** attempt
                    logger.warning("%s %s: HTTP %s, retrying in %ss", self.alias, api, e.code, wait)
                    time.sleep(wait)
                    continue
                raise PlayFabError(f"{api}: {data.get('errorMessage') or data}")
        raise PlayFabError(f"{api}: gave up after 5 attempts")
