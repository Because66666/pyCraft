"""
Microsoft (MSA) authentication for Minecraft: Java Edition, ported
from `prismarine-auth <https://github.com/PrismarineJS/prismarine-auth>`_.

Only the OAuth 2.0 device-code flow is implemented: no password is
required, the user authorizes the login in a browser. Tokens are cached
on disk (see :class:`minecraft.microsoft.cache.FileCache`) so that
subsequent runs usually need no interaction.
"""
from .auth_flow import MicrosoftAuthFlow
from .constants import ENDPOINTS, Titles, XBOX_LIVE_ERRORS
from .cache import FileCache

__all__ = [
    "MicrosoftAuthFlow",
    "ENDPOINTS",
    "Titles",
    "XBOX_LIVE_ERRORS",
    "FileCache",
]
