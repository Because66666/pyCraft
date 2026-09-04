"""
Token manager for Xbox Live (XBL user/device/title tokens and XSTS),
ported from ``prismarine-auth``
(``src/TokenManagers/XboxTokenManager.js``).

Requests to the Xbox Live endpoints are proof-of-possession signed with
an ephemeral P-256 EC key; see ``XboxTokenManager.sign``.
"""
import base64
import datetime
import json
import struct
import time
import uuid

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature)

from ..exceptions import YggdrasilError
from .constants import ENDPOINTS, XBOX_LIVE_ERRORS
from .util import check_status, create_hash

try:
    from urllib.parse import urlparse
except ImportError:  # Python 2
    from urlparse import urlparse

#: Difference between the Unix and Windows (NT) epochs, in seconds.
WINDOWS_EPOCH_OFFSET = 11644473600


class XboxTokenManager(object):
    """
    Manages Xbox Live tokens for ``xboxlive.com``. Only the token
    exchange steps are implemented (no password-based 'replay' auth and
    no 'sisu' flow).
    """

    def __init__(self, cache):
        """
        Parameters:
            cache - A ``FileCache`` used to persist the tokens.
        """
        self.key = ec.generate_private_key(ec.SECP256R1())
        public_numbers = self.key.public_key().public_numbers()
        self.jwk = {
            "kty": "EC",
            "crv": "P-256",
            "x": _int_to_b64url(public_numbers.x),
            "y": _int_to_b64url(public_numbers.y),
            "alg": "ES256",
            "use": "sig",
        }
        self.cache = cache
        self.headers = {
            "Cache-Control": "no-store, must-revalidate, no-cache",
            "x-xbl-contract-version": "1",
        }

    def get_cached_tokens(self, relying_party):
        """
        Returns a dict with ``user_token``, ``title_token``,
        ``device_token`` and ``xsts_token`` entries. Each entry has a
        ``valid`` flag and, when valid, the cached ``token``/``data``.
        """
        cached = self.cache.get_cached()
        xsts_hash = create_hash(relying_party)

        result = {}
        for token_name in ("userToken", "titleToken", "deviceToken"):
            cached_token = cached.get(token_name)
            if cached_token and _not_after_valid(
                    cached_token.get("NotAfter")):
                result[token_name] = {
                    "valid": True,
                    "token": cached_token["Token"],
                    "data": cached_token,
                }
            else:
                result[token_name] = {"valid": False}

        xsts_token = cached.get(xsts_hash)
        if xsts_token and _not_after_valid(xsts_token.get("expiresOn")):
            result["xstsToken"] = {"valid": True, "data": xsts_token}
        else:
            result["xstsToken"] = {"valid": False}
        return result

    def sign(self, url, authorization_token, payload):
        """
        Creates the proof-of-possession signature header for a request
        to an Xbox Live endpoint and returns it as raw bytes (base64
        encoding is left to the caller).

        Ported from ``XboxTokenManager.sign`` in prismarine-auth: the
        signed buffer is ``int32BE(1) | 0x00 | uint64BE(windows_ts) |
        0x00 | "POST\\0" | path\\0 | token\\0 | payload\\0``, signed with
        ECDSA/SHA-256, and the header is ``int32BE(1) |
        uint64BE(windows_ts) | signature`` with the signature in
        IEEE P1363 form (r and s as 32-byte big-endian integers).
        """
        windows_timestamp = (
            int(time.time()) + WINDOWS_EPOCH_OFFSET) * 10000000
        path_and_query = urlparse(url).path

        buf = struct.pack(">i", 1)
        buf += b"\x00"
        buf += struct.pack(">Q", windows_timestamp)
        buf += b"\x00"
        for part in ("POST", path_and_query, authorization_token,
                     payload):
            buf += part.encode("utf-8") + b"\x00"

        der_signature = self.key.sign(buf, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der_signature)
        signature = _int_to_bytes(r) + _int_to_bytes(s)

        header = struct.pack(">iQ", 1, windows_timestamp)
        return header + signature

    def get_user_token(self, access_token):
        """
        Exchanges an MSA access token for an Xbox Live user token.
        """
        payload = {
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": "t=" + access_token,
            },
        }
        url = ENDPOINTS["xbox"]["user_auth"]
        body = _json_dumps(payload)
        headers = dict(self.headers)
        headers.update({
            "signature": _b64(self.sign(url, "", body)),
            "Content-Type": "application/json",
            "accept": "application/json",
            "x-xbl-contract-version": "2",
        })
        ret = check_status(requests.post(
            url, data=body, headers=headers, timeout=15))
        self.cache.set_cached_partial({"userToken": ret})
        return ret["Token"]

    def get_device_token(self, as_device=None):
        """
        Requests an Xbox Live device token that uniquely links the
        XSTS token to a (virtual) device.
        """
        as_device = as_device or {}
        payload = {
            "Properties": {
                "AuthMethod": "ProofOfPossession",
                "Id": "{" + _next_uuid() + "}",
                "DeviceType": as_device.get("device_type", "Nintendo"),
                "SerialNumber": "{" + _next_uuid() + "}",
                "Version": as_device.get("device_version", "0.0.0"),
                "ProofKey": self.jwk,
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        }
        url = ENDPOINTS["xbox"]["device_auth"]
        body = _json_dumps(payload)
        headers = dict(self.headers)
        headers["Signature"] = _b64(self.sign(url, "", body))
        ret = check_status(requests.post(
            url, data=body, headers=headers, timeout=15))
        self.cache.set_cached_partial({"deviceToken": ret})
        return ret["Token"]

    def get_title_token(self, msa_access_token, device_token):
        """
        Requests an Xbox Live title token. Only works with live.com
        (device-code flow) auth.
        """
        payload = {
            "Properties": {
                "AuthMethod": "RPS",
                "DeviceToken": device_token,
                "RpsTicket": "t=" + msa_access_token,
                "SiteName": "user.auth.xboxlive.com",
                "ProofKey": self.jwk,
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        }
        url = ENDPOINTS["xbox"]["title_auth"]
        body = _json_dumps(payload)
        headers = dict(self.headers)
        headers["Signature"] = _b64(self.sign(url, "", body))
        ret = check_status(requests.post(
            url, data=body, headers=headers, timeout=15))
        self.cache.set_cached_partial({"titleToken": ret})
        return ret["Token"]

    def get_xsts_token(self, tokens, relying_party):
        """
        Exchanges user (and optionally device/title) tokens for an XSTS
        token for the given relying party.

        Parameters:
            tokens - A dict with ``user_token`` and optionally
                ``device_token`` and ``title_token``.
            relying_party - e.g. ``rp://api.minecraftservices.com/``.
        """
        payload = {
            "RelyingParty": relying_party,
            "TokenType": "JWT",
            "Properties": {
                "UserTokens": [tokens["user_token"]],
                "DeviceToken": tokens.get("device_token"),
                "TitleToken": tokens.get("title_token"),
                "ProofKey": self.jwk,
                "SandboxId": "RETAIL",
            },
        }
        url = ENDPOINTS["xbox"]["xsts_authorize"]
        body = _json_dumps(payload)
        headers = dict(self.headers)
        headers["Signature"] = _b64(self.sign(url, "", body))

        res = requests.post(url, data=body, headers=headers, timeout=15)
        if not 200 <= res.status_code < 300:
            self.check_token_error(res.json().get("XErr"), res.json())

        ret = res.json()
        xsts = {
            "userXUID": ret["DisplayClaims"]["xui"][0].get("xid"),
            "userHash": ret["DisplayClaims"]["xui"][0]["uhs"],
            "XSTSToken": ret["Token"],
            "expiresOn": ret["NotAfter"],
        }
        self.cache.set_cached_partial({create_hash(relying_party): xsts})
        return xsts

    @staticmethod
    def check_token_error(error_code, response):
        """
        Raises a :class:`minecraft.exceptions.YggdrasilError` with a
        human-readable message for a known Xbox Live ``XErr`` code.
        """
        if error_code in XBOX_LIVE_ERRORS:
            raise YggdrasilError(XBOX_LIVE_ERRORS[error_code])
        raise YggdrasilError(
            "Xbox Live authentication failed to obtain a XSTS token. "
            "XErr: {0}\n{1}".format(error_code, response))


def _now_ms():
    return int(time.time() * 1000)


def _not_after_valid(expires):
    """
    Returns ``True`` when the ISO-8601 timestamp ``expires`` is more
    than a second in the future.
    """
    if not expires:
        return False
    epoch = datetime.datetime(1970, 1, 1)
    expires_ts = (_parse_iso8601(expires) - epoch).total_seconds()
    remaining_ms = int((expires_ts - time.time()) * 1000)
    return remaining_ms > 1000


def _parse_iso8601(value):
    value = value.rstrip("Z")
    if "." in value:
        main, fraction = value.split(".", 1)
        # ``strptime`` supports at most 6 fractional digits, while the
        # Xbox Live endpoints may return 7.
        return datetime.datetime.strptime(
            main + "." + fraction[:6], "%Y-%m-%dT%H:%M:%S.%f")
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def _next_uuid():
    return str(uuid.uuid3(
        uuid.NAMESPACE_DNS, str(_now_ms())))


def _int_to_bytes(value):
    return value.to_bytes(32, "big")


def _int_to_b64url(value):
    return base64.urlsafe_b64encode(
        _int_to_bytes(value)).decode("ascii").rstrip("=")


def _b64(data):
    return base64.b64encode(data).decode("ascii")


def _json_dumps(payload):
    return json.dumps(payload)
