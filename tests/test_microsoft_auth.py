"""
Offline tests for the Microsoft authentication component
(``minecraft.microsoft`` and ``MicrosoftAuthenticationToken``). All
HTTP traffic is mocked; the real device-code flow requires human
interaction and cannot be tested automatically.
"""
import datetime
import hashlib
import json
import os
import shutil
import struct
import tempfile
import unittest

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    encode_dss_signature)

try:
    from unittest import mock
except ImportError:  # Python 2
    import mock

from minecraft.authentication import (
    MicrosoftAuthenticationToken, SESSION_SERVER)
from minecraft.exceptions import YggdrasilError
from minecraft.microsoft.auth_flow import MicrosoftAuthFlow
from minecraft.microsoft.cache import FileCache
from minecraft.microsoft.constants import ENDPOINTS, Titles
from minecraft.microsoft.util import create_hash
from minecraft.microsoft.xbox_token_manager import XboxTokenManager

FUTURE = (datetime.datetime.now(datetime.timezone.utc)
          .replace(tzinfo=None)
          + datetime.timedelta(days=1)).isoformat() + "Z"
PROFILE = {"id": "8667ba71b85a4004af54457a9734eed7", "name": "Steve"}


class FakeResponse(object):
    def __init__(self, status_code=200, json_data=None, cookies=None):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = json.dumps(self._json_data)
        self.cookies = cookies or {}

    def json(self):
        return self._json_data


class MockDispatcher(object):
    """
    Answers the HTTP requests of the whole authentication chain with
    canned responses. The first device-code poll answers
    ``authorization_pending`` to exercise the polling loop.
    """

    def __init__(self):
        self.calls = []
        self.poll_count = 0

    def post(self, url, **kwargs):
        self.calls.append(url)
        endpoints = ENDPOINTS
        if url == endpoints["live"]["device_code_request"]:
            return FakeResponse(200, {
                "device_code": "device_code",
                "user_code": "ABCD1234",
                "verification_uri": "https://www.microsoft.com/link",
                "expires_in": 900,
                "interval": 0,
            })
        if url.startswith(endpoints["live"]["token_request"]):
            self.poll_count += 1
            if self.poll_count == 1:
                return FakeResponse(200, {
                    "error": "authorization_pending"})
            return FakeResponse(200, {
                "access_token": "msa_access_token",
                "refresh_token": "msa_refresh_token",
                "expires_in": 3600,
                "token_type": "bearer",
            })
        if url == endpoints["xbox"]["user_auth"]:
            return FakeResponse(200, {
                "Token": "xbl_user_token", "NotAfter": FUTURE})
        if url == endpoints["xbox"]["device_auth"]:
            return FakeResponse(200, {
                "Token": "xbl_device_token", "NotAfter": FUTURE})
        if url == endpoints["xbox"]["title_auth"]:
            return FakeResponse(200, {
                "Token": "xbl_title_token", "NotAfter": FUTURE})
        if url == endpoints["xbox"]["xsts_authorize"]:
            return FakeResponse(200, {
                "Token": "xsts_token",
                "NotAfter": FUTURE,
                "DisplayClaims": {"xui": [{"uhs": "user_hash",
                                           "xid": "123"}]},
            })
        if url == endpoints["minecraft_java"]["login_with_xbox"]:
            return FakeResponse(200, {
                "access_token": "mc_access_token",
                "expires_in": 86400,
                "token_type": "Bearer",
            })
        if url == endpoints["minecraft_java"]["certificates"]:
            return FakeResponse(200, {"keyPair": {"publicKey": "pub",
                                                  "privateKey": "priv"}})
        raise AssertionError("Unexpected POST to " + url)

    def get(self, url, **kwargs):
        self.calls.append(url)
        if url == ENDPOINTS["minecraft_java"]["profile"]:
            return FakeResponse(200, PROFILE)
        raise AssertionError("Unexpected GET to " + url)


def patch_requests(dispatcher):
    """
    Patches ``requests`` in every token manager module with the given
    dispatcher. Returns the list of started patchers.
    """
    patchers = []
    for module in ("live_token_manager", "xbox_token_manager",
                   "java_token_manager"):
        patcher = mock.patch(
            "minecraft.microsoft.{0}.requests".format(module))
        patched = patcher.start()
        patched.post.side_effect = \
            lambda *args, **kwargs: dispatcher.post(*args, **kwargs)
        patched.get.side_effect = \
            lambda *args, **kwargs: dispatcher.get(*args, **kwargs)
        patchers.append(patcher)
    return patchers


class FileCacheTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.location = os.path.join(self.dir, "cache.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_missing_file_resets_to_empty(self):
        cache = FileCache(self.location)
        self.assertEqual(cache.get_cached(), {})

    def test_roundtrip(self):
        cache = FileCache(self.location)
        cache.set_cached({"token": {"access_token": "abc"}})
        self.assertEqual(FileCache(self.location).get_cached(),
                         {"token": {"access_token": "abc"}})

    def test_set_cached_partial_merges(self):
        cache = FileCache(self.location)
        cache.set_cached({"a": 1})
        cache.set_cached_partial({"b": 2})
        self.assertEqual(cache.get_cached(), {"a": 1, "b": 2})

    def test_corrupt_file_resets(self):
        with open(self.location, "w") as cache_file:
            cache_file.write("not json")
        self.assertEqual(FileCache(self.location).get_cached(), {})


class CreateHashTest(unittest.TestCase):
    def test_matches_sha1_prefix(self):
        for value in ("", "user@example.com",
                      "rp://api.minecraftservices.com/"):
            self.assertEqual(
                create_hash(value),
                hashlib.sha1(value.encode("utf-8")).hexdigest()[:6])

    def test_none_hashes_like_empty_string(self):
        self.assertEqual(create_hash(None), create_hash(""))


class XboxSignTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.manager = XboxTokenManager(
            FileCache(os.path.join(self.dir, "xbl-cache.json")))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_header_structure_and_signature(self):
        url = ENDPOINTS["xbox"]["user_auth"]
        payload = json.dumps({"RelyingParty": "http://auth.xboxlive.com"})
        header = self.manager.sign(url, "", payload)

        # int32BE version + uint64BE timestamp + 64-byte P1363 signature.
        self.assertEqual(len(header), 4 + 8 + 64)
        version, timestamp = struct.unpack(">iQ", header[:12])
        self.assertEqual(version, 1)

        # Rebuild the signed buffer with the timestamp from the header.
        buf = struct.pack(">i", 1) + b"\x00"
        buf += struct.pack(">Q", timestamp) + b"\x00"
        for part in ("POST", "/user/authenticate", "", payload):
            buf += part.encode("utf-8") + b"\x00"

        r = int.from_bytes(header[12:44], "big")
        s = int.from_bytes(header[44:76], "big")
        der_signature = encode_dss_signature(r, s)
        # Raises ``InvalidSignature`` when the signature is wrong.
        self.manager.key.public_key().verify(
            der_signature, buf, ec.ECDSA(hashes.SHA256()))

    def test_jwk(self):
        jwk = self.manager.jwk
        self.assertEqual(jwk["kty"], "EC")
        self.assertEqual(jwk["crv"], "P-256")
        self.assertEqual(jwk["alg"], "ES256")
        self.assertEqual(jwk["use"], "sig")


class CheckTokenErrorTest(unittest.TestCase):
    def test_known_xerr_raises_human_readable_error(self):
        with self.assertRaises(YggdrasilError) as context:
            XboxTokenManager.check_token_error(2148916233, {})
        self.assertIn("does not have an Xbox profile",
                      str(context.exception))

    def test_unknown_xerr(self):
        with self.assertRaises(YggdrasilError) as context:
            XboxTokenManager.check_token_error(1234, {"some": "response"})
        self.assertIn("XErr: 1234", str(context.exception))


class MicrosoftAuthFlowTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.dispatcher = MockDispatcher()
        self.patchers = patch_requests(self.dispatcher)

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()
        shutil.rmtree(self.dir, ignore_errors=True)

    def make_token(self):
        return MicrosoftAuthenticationToken()

    def authenticate(self, token, **kwargs):
        kwargs.setdefault("cache_dir", self.dir)
        return token.authenticate(**kwargs)

    def test_full_device_code_flow(self):
        device_codes = []
        token = self.make_token()
        self.assertTrue(self.authenticate(
            token, on_device_code=device_codes.append))

        self.assertTrue(token.authenticated)
        self.assertEqual(token.access_token, "mc_access_token")
        self.assertEqual(token.username, "Steve")
        self.assertEqual(token.profile.id_, PROFILE["id"])
        self.assertEqual(token.profile.name, "Steve")

        # The device code was shown to the user exactly once and the
        # poll loop handled ``authorization_pending``.
        self.assertEqual(len(device_codes), 1)
        self.assertEqual(device_codes[0]["user_code"], "ABCD1234")
        self.assertIn("microsoft.com/link", device_codes[0]["message"])
        self.assertEqual(self.dispatcher.poll_count, 2)

        # The three cache files of the 'live' flow were created.
        cache_files = os.listdir(self.dir)
        for name in ("live", "xbl", "mca"):
            self.assertTrue(
                any(f.endswith("_{0}-cache.json".format(name))
                    for f in cache_files),
                "missing cache file for " + name)

    def test_cached_tokens_are_reused(self):
        token = self.make_token()
        self.authenticate(token, on_device_code=lambda data: None)

        # Second run with a fresh token object: the cached Minecraft
        # token is still valid, so only the profile may be fetched.
        dispatcher = MockDispatcher()

        def fail_on_post(url, **kwargs):
            raise AssertionError(
                "Expected cached tokens to be reused, got POST to "
                + url)

        dispatcher.post = fail_on_post
        for patcher in self.patchers:
            patcher.stop()
        self.patchers = patch_requests(dispatcher)

        token2 = self.make_token()
        self.assertTrue(self.authenticate(token2))
        self.assertEqual(token2.access_token, "mc_access_token")
        self.assertEqual(token2.username, "Steve")
        self.assertEqual(dispatcher.calls,
                         [ENDPOINTS["minecraft_java"]["profile"]])

    def test_missing_profile_raises(self):
        def no_profile_get(url, **kwargs):
            return FakeResponse(200, {"error": "NOT_FOUND"})

        self.dispatcher.get = no_profile_get
        token = self.make_token()
        with self.assertRaises(YggdrasilError) as context:
            self.authenticate(token, on_device_code=lambda data: None)
        self.assertIn("does the account own minecraft?",
                      str(context.exception))

    def test_auth_flow_requires_auth_title(self):
        with self.assertRaises(ValueError):
            MicrosoftAuthFlow("", self.dir, {})

    def test_auth_flow_rejects_non_live_flow(self):
        with self.assertRaises(ValueError):
            MicrosoftAuthFlow("", self.dir,
                              {"flow": "msal",
                               "auth_title": Titles.MinecraftJava})


class MicrosoftJoinTest(unittest.TestCase):
    def test_join_posts_to_session_server(self):
        token = MicrosoftAuthenticationToken()
        token.access_token = "mc_access_token"
        token.profile.id_ = PROFILE["id"]
        token.profile.name = PROFILE["name"]

        with mock.patch(
                "minecraft.authentication._make_request") as make_request:
            make_request.return_value = FakeResponse(204)
            self.assertTrue(token.join("server-id"))

        make_request.assert_called_once_with(
            SESSION_SERVER, "join",
            {"accessToken": "mc_access_token",
             "selectedProfile": PROFILE,
             "serverId": "server-id"})

    def test_join_requires_authentication(self):
        token = MicrosoftAuthenticationToken()
        self.assertRaises(YggdrasilError, token.join, "server-id")


if __name__ == "__main__":
    unittest.main()
