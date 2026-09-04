"""
Orchestrates the Microsoft authentication chain (MSA device-code
login -> Xbox Live tokens -> Minecraft Services token), ported from
``prismarine-auth`` (``src/MicrosoftAuthFlow.js``).

Only the ``live`` (device code) flow is supported; password-based and
MSAL flows are intentionally not ported.
"""
import os
import time

from .cache import FileCache
from .constants import ENDPOINTS, XBOX_LIVE_SCOPE
from .java_token_manager import MinecraftJavaTokenManager
from .live_token_manager import LiveTokenManager
from .util import create_hash
from .xbox_token_manager import XboxTokenManager

#: Cache ids that may be requested from the cache factory.
CACHE_IDS = ("live", "xbl", "mca")


def _retry(method_fn, before_retry, times):
    """
    Calls ``method_fn`` up to ``times`` times, calling
    ``before_retry`` and sleeping 2 seconds between attempts.
    """
    while times > 0:
        times -= 1
        if times != 0:
            try:
                return method_fn()
            except Exception:
                time.sleep(2)
                before_retry()
        else:
            return method_fn()


class MicrosoftAuthFlow(object):
    """
    Implements the Microsoft authentication flow for Minecraft: Java
    Edition using the OAuth 2.0 device-code grant. Tokens are cached on
    disk so that subsequent runs usually need no user interaction.
    """

    def __init__(self, username="", cache=None, options=None,
                 code_callback=None):
        """
        Parameters:
            username - The Microsoft account's username/email. Only
                used to name the cache files; may be empty.
            cache - A directory path where the token cache files are
                stored, or a callable ``cache(cache_name, username)``
                returning a ``FileCache``-compatible object.
            options - A dict. Supported keys: ``auth_title`` (required;
                a client id from ``constants.Titles``), ``device_type``
                and ``device_version`` (device token parameters) and
                ``force_refresh`` (discard cached tokens).
            code_callback - Called with the device-code response dict
                when user interaction is required.
        """
        options = options or {}
        if options.get("flow", "live") != "live":
            raise ValueError("Only the 'live' (device code) flow is "
                             "supported.")
        if not options.get("auth_title"):
            raise ValueError("Please specify an 'auth_title' in the "
                             "options when using the live flow.")

        self.username = username
        self.options = options
        self.code_callback = code_callback

        if not callable(cache):
            cache = _file_cache_factory(cache, username,
                                        options.get("force_refresh"))

        self.msa = LiveTokenManager(options["auth_title"],
                                    XBOX_LIVE_SCOPE,
                                    cache("live", username))
        self.xbl = XboxTokenManager(cache("xbl", username))
        self.mca = MinecraftJavaTokenManager(cache("mca", username))

    def get_msa_token(self):
        """
        Returns a Microsoft account access token, using the cache when
        possible and the device-code flow otherwise.
        """
        if self.msa.verify_tokens():
            return self.msa.get_access_token()["token"]

        def default_callback(response):
            print("[msa] First time signing in. Please authenticate "
                  "now:")
            print(response["message"])

        callback = self.code_callback or default_callback
        ret = self.msa.auth_device_code(callback)
        return ret["access_token"]

    def get_xbox_token(self, relying_party=None, force_refresh=False):
        """
        Returns an XSTS token dict (``userHash``, ``XSTSToken``,
        ``expiresOn``, ``userXUID``) for the given relying party.
        """
        if relying_party is None:
            relying_party = ENDPOINTS["xbox"]["relying_party"]
        cached = self.xbl.get_cached_tokens(relying_party)
        if cached["xstsToken"]["valid"] and not force_refresh:
            return cached["xstsToken"]["data"]

        def obtain_tokens():
            msa_token = self.get_msa_token()
            user_token = (cached["userToken"].get("token")
                          or self.xbl.get_user_token(msa_token))
            device_token = (cached["deviceToken"].get("token")
                            or self.xbl.get_device_token(self.options))
            title_token = (cached["titleToken"].get("token")
                           or self.xbl.get_title_token(msa_token,
                                                       device_token))
            return self.xbl.get_xsts_token(
                {"user_token": user_token, "device_token": device_token,
                 "title_token": title_token}, relying_party)

        def force_msa_refresh():
            self.msa.force_refresh = True

        return _retry(obtain_tokens, force_msa_refresh, 2)

    def get_minecraft_java_token(self, fetch_profile=False,
                                 fetch_certificates=False):
        """
        Returns a dict with a Minecraft access ``token`` and, when
        requested, the account's ``profile`` and ``certificates``.
        """
        response = {"token": "", "profile": {}}
        if self.mca.verify_tokens():
            response["token"] = \
                self.mca.get_cached_access_token()["token"]
        else:
            def obtain_token():
                xsts = self.get_xbox_token(
                    ENDPOINTS["minecraft_java"]["xsts_relying_party"])
                response["token"] = self.mca.get_access_token(xsts)

            def force_xbl_refresh():
                self.xbl.force_refresh = True

            _retry(obtain_token, force_xbl_refresh, 2)

        if fetch_profile:
            response["profile"] = self.mca.fetch_profile(
                response["token"])
        if fetch_certificates:
            response["certificates"] = self.mca.fetch_certificates(
                response["token"])
        return response


def _file_cache_factory(cache_path, username, force_refresh=False):
    """
    Returns a ``cache(cache_name, username)`` factory that creates
    ``FileCache`` objects inside ``cache_path``, with file names of the
    form ``<sha1(username)[:6]>_<cache_name>-cache.json`` (the same
    naming scheme as prismarine-auth).
    """
    if cache_path is None:
        cache_path = os.path.join(os.path.expanduser("~"), ".minecraft",
                                  "nmp-cache")
    if not os.path.isdir(cache_path):
        os.makedirs(cache_path)

    def factory(cache_name, _username):
        if cache_name not in CACHE_IDS:
            raise ValueError("Cannot instantiate cache for unknown ID: "
                             "'{0}'".format(cache_name))
        file_name = "{0}_{1}-cache.json".format(
            create_hash(username), cache_name)
        cache = FileCache(os.path.join(cache_path, file_name))
        if force_refresh:
            cache.reset()
        return cache

    return factory
