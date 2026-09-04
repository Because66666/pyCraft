"""
Small helpers shared by the Microsoft authentication token managers,
ported from ``prismarine-auth`` (``src/common/Util.js``).
"""
import hashlib

from ..exceptions import YggdrasilError


def check_status(res):
    """
    Returns the JSON body of ``res`` if it carries a 2xx status code,
    otherwise raises a :class:`minecraft.exceptions.YggdrasilError`.

    Parameters:
        res - A ``requests.Response`` object.
    """
    if 200 <= res.status_code < 300:
        return res.json()
    message = "[{status_code}] {response_text}".format(
        status_code=res.status_code, response_text=res.text)
    raise YggdrasilError(message)


def create_hash(input_string):
    """
    Returns the first 6 characters of the SHA-1 hex digest of the
    given string, matching ``createHash`` in prismarine-auth. Used to
    derive cache file names and XSTS cache keys.
    """
    if input_string is None:
        input_string = ""
    return hashlib.sha1(input_string.encode("utf-8")).hexdigest()[:6]
