"""
Token manager for the Minecraft Services API (Java edition), ported
from ``prismarine-auth``
(``src/TokenManagers/MinecraftJavaTokenManager.js``).
"""
import time

import requests

from .constants import ENDPOINTS, MINECRAFT_SERVICES_HEADERS
from .util import check_status


class MinecraftJavaTokenManager(object):
    """
    Exchanges an XSTS token for a Minecraft access token and fetches
    the associated profile and (optionally) chat-signing certificates.
    """

    def __init__(self, cache):
        """
        Parameters:
            cache - A ``FileCache`` used to persist the access token.
        """
        self.cache = cache
        self.force_refresh = False

    def get_cached_access_token(self):
        """
        Returns ``{"valid": bool, "until": int, "token": str, "data":
        dict}`` for the cached Minecraft access token, or ``None`` when
        no token is cached.
        """
        token = self.cache.get_cached().get("mca")
        if not token:
            return None
        expires = token["obtainedOn"] + token["expires_in"] * 1000
        valid = expires - _now_ms() > 1000
        return {"valid": valid, "until": expires,
                "token": token["access_token"], "data": token}

    def set_cached_access_token(self, data):
        """
        Stores a Minecraft token response in the cache, recording when
        it was obtained.
        """
        token = dict(data)
        token["obtainedOn"] = _now_ms()
        self.cache.set_cached_partial({"mca": token})

    def verify_tokens(self):
        """
        Returns ``True`` when the cached Minecraft access token is
        still valid.
        """
        cached = self.get_cached_access_token()
        if not cached or self.force_refresh:
            return False
        return cached["valid"]

    def get_access_token(self, xsts):
        """
        Exchanges an XSTS token (as returned by
        ``XboxTokenManager.get_xsts_token``) for a Minecraft access
        token.
        """
        headers = dict(MINECRAFT_SERVICES_HEADERS)
        identity_token = "XBL3.0 x={0};{1}".format(
            xsts["userHash"], xsts["XSTSToken"])
        ret = check_status(requests.post(
            ENDPOINTS["minecraft_java"]["login_with_xbox"],
            json={"identityToken": identity_token},
            headers=headers, timeout=15))
        self.set_cached_access_token(ret)
        return ret["access_token"]

    def fetch_profile(self, access_token):
        """
        Fetches the Minecraft profile (``id`` and ``name``) belonging
        to the given access token.
        """
        headers = dict(MINECRAFT_SERVICES_HEADERS)
        headers["Authorization"] = "Bearer " + access_token
        return check_status(requests.get(
            ENDPOINTS["minecraft_java"]["profile"],
            headers=headers, timeout=15))

    def fetch_certificates(self, access_token):
        """
        Fetches the chat-signing key pair and certificates used by
        Minecraft 1.19+.
        """
        headers = dict(MINECRAFT_SERVICES_HEADERS)
        headers["Authorization"] = "Bearer " + access_token
        return check_status(requests.post(
            ENDPOINTS["minecraft_java"]["certificates"],
            headers=headers, timeout=15))


def _now_ms():
    return int(time.time() * 1000)
