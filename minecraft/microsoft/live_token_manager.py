"""
Token manager for the ``login.live.com`` OAuth 2.0 device-code flow,
ported from ``prismarine-auth``
(``src/TokenManagers/LiveTokenManager.js``).
"""
import time

import requests

from ..exceptions import YggdrasilError
from .constants import ENDPOINTS
from .util import check_status

#: OAuth 2.0 grant type used when polling with a device code.
DEVICE_CODE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


class LiveTokenManager(object):
    """
    Obtains and caches Microsoft account (MSA) tokens via the
    ``login.live.com`` device-code flow. No password is involved: the
    user authorizes the device code in a browser.
    """

    def __init__(self, client_id, scopes, cache):
        """
        Parameters:
            client_id - The OAuth client id (a title id from
                ``minecraft.microsoft.constants.Titles``).
            scopes - A space-separated string of OAuth scopes.
            cache - A ``FileCache`` used to persist the tokens.
        """
        self.client_id = client_id
        self.scopes = scopes
        self.cache = cache
        self.force_refresh = False

    def verify_tokens(self):
        """
        Returns ``True`` when a usable (cached or refreshed) access
        token is available.
        """
        if self.force_refresh:
            try:
                self.refresh_tokens()
            except Exception:
                pass
        access_token = self.get_access_token()
        refresh_token = self.get_refresh_token()
        if not access_token or not refresh_token:
            return False
        if access_token["valid"] and refresh_token:
            return True
        try:
            self.refresh_tokens()
            return True
        except Exception:
            return False

    def refresh_tokens(self):
        """
        Exchanges the cached refresh token for a new token pair.

        Raises:
            ValueError - if no refresh token is cached.
        """
        refresh_token = self.get_refresh_token()
        if not refresh_token:
            raise ValueError("Cannot refresh without refresh token")

        data = {
            "scope": self.scopes,
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token["token"],
        }
        token = check_status(requests.post(
            ENDPOINTS["live"]["token_request"], data=data, timeout=15))
        self.update_cache(token)
        return token

    def get_access_token(self):
        """
        Returns ``{"valid": bool, "until": int, "token": str}`` for the
        cached access token, or ``None`` when no token is cached.
        """
        token = self.cache.get_cached().get("token")
        if not token:
            return None
        until = token["obtainedOn"] + token["expires_in"] * 1000
        valid = until - _now_ms() > 1000
        return {"valid": valid, "until": until,
                "token": token["access_token"]}

    def get_refresh_token(self):
        """
        Returns ``{"valid": bool, "until": int, "token": str}`` for the
        cached refresh token, or ``None`` when no token is cached.
        """
        token = self.cache.get_cached().get("token")
        if not token:
            return None
        until = token["obtainedOn"] + token["expires_in"] * 1000
        valid = until - _now_ms() > 1000
        return {"valid": valid, "until": until,
                "token": token["refresh_token"]}

    def update_cache(self, data):
        """
        Stores a token response in the cache, recording when it was
        obtained.
        """
        token = dict(data)
        token["obtainedOn"] = _now_ms()
        self.cache.set_cached_partial({"token": token})

    def auth_device_code(self, device_code_callback):
        """
        Runs the OAuth 2.0 device-code flow: requests a device code,
        passes it to ``device_code_callback`` (which should show it to
        the user) and polls until the user authorizes the code.

        The callback receives a dict with (among others) the keys
        ``verification_uri``, ``user_code`` and ``message``.

        Returns:
            A dict with the obtained ``access_token``.

        Raises:
            minecraft.exceptions.YggdrasilError - on failure or timeout.
        """
        data = {
            "scope": self.scopes,
            "client_id": self.client_id,
            "response_type": "device_code",
        }
        res = requests.post(
            ENDPOINTS["live"]["device_code_request"], data=data,
            timeout=15)
        if res.status_code != 200:
            raise YggdrasilError(
                "Failed to request live.com device code: " + res.text)
        cookies = res.cookies
        res_data = check_status(res)
        res_data["message"] = (
            "To sign in, use a web browser to open the page {uri} and "
            "use the code {code} or visit "
            "http://microsoft.com/link?otc={code}").format(
                uri=res_data["verification_uri"],
                code=res_data["user_code"])
        device_code_callback(res_data)

        expire_time = time.time() + res_data["expires_in"] - 0.1
        interval = res_data.get("interval", 5)
        while time.time() < expire_time:
            time.sleep(interval)
            poll_data = {
                "client_id": self.client_id,
                "device_code": res_data["device_code"],
                "grant_type": DEVICE_CODE_GRANT,
            }
            token_res = requests.post(
                ENDPOINTS["live"]["token_request"] + "?client_id="
                + self.client_id,
                data=poll_data, cookies=cookies, timeout=15).json()
            if "error" in token_res:
                if token_res["error"] == "authorization_pending":
                    continue
                raise YggdrasilError(
                    "Failed to acquire authorization code from device "
                    "token ({error}) - {description}".format(
                        error=token_res["error"],
                        description=token_res.get("error_description")))
            self.update_cache(token_res)
            return {"access_token": token_res["access_token"]}
        raise YggdrasilError("Authentication failed, timed out")


def _now_ms():
    return int(time.time() * 1000)
