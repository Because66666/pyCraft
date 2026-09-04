"""
Constants for the Microsoft / Xbox Live / Minecraft Services
authentication chain, ported from ``prismarine-auth``
(``src/common/Constants.js`` and ``src/common/Titles.js``).
"""

#: The OAuth 2.0 scope used by the 'live' device-code flow.
XBOX_LIVE_SCOPE = "service::user.auth.xboxlive.com::MBI_SSL"

#: Endpoints used during the authentication chain.
ENDPOINTS = {
    "minecraft_java": {
        "xsts_relying_party": "rp://api.minecraftservices.com/",
        "login_with_xbox":
            "https://api.minecraftservices.com/authentication/"
            "login_with_xbox",
        "profile": "https://api.minecraftservices.com/minecraft/profile",
        "certificates":
            "https://api.minecraftservices.com/player/certificates",
    },
    "xbox": {
        "relying_party": "http://xboxlive.com",
        "device_auth": "https://device.auth.xboxlive.com/device/authenticate",
        "title_auth": "https://title.auth.xboxlive.com/title/authenticate",
        "user_auth": "https://user.auth.xboxlive.com/user/authenticate",
        "xsts_authorize": "https://xsts.auth.xboxlive.com/xsts/authorize",
    },
    "live": {
        "device_code_request": "https://login.live.com/oauth20_connect.srf",
        "token_request": "https://login.live.com/oauth20_token.srf",
    },
}


#: Client ids of official Microsoft titles that may be used with the
#: device-code flow.
class Titles(object):
    MinecraftNintendoSwitch = "00000000441cc96b"
    MinecraftPlaystation = "000000004827c78e"
    MinecraftAndroid = "0000000048183522"
    MinecraftJava = "00000000402b5328"
    MinecraftIOS = "000000004c17c01a"
    XboxAppIOS = "000000004c12ae6f"
    XboxGamepassIOS = "000000004c20a908"


#: Headers sent to the Minecraft Services API.
MINECRAFT_SERVICES_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "MinecraftLauncher/2.2.10675",
}

#: Human-readable messages for known Xbox Live ``XErr`` error codes.
#: See http://wiki.vg/Microsoft_Authentication_Scheme
XBOX_LIVE_ERRORS = {
    2148916227: "Your account was banned by Xbox for violating one or more "
                "Community Standards for Xbox and is unable to be used.",
    2148916229: "Your account is currently restricted and your guardian has "
                "not given you permission to play online. Login to "
                "https://account.microsoft.com/family/ and have your "
                "guardian change your permissions.",
    2148916233: "Your account currently does not have an Xbox profile. "
                "Please create one at https://signup.live.com/signup",
    2148916234: "Your account has not accepted Xbox's Terms of Service. "
                "Please login and accept them.",
    2148916235: "Your account resides in a region that Xbox has not "
                "authorized use from. Xbox has blocked your attempt at "
                "logging in.",
    2148916236: "Your account requires proof of age. Please login to "
                "https://login.live.com/login.srf and provide proof of age.",
    2148916237: "Your account has reached the its limit for playtime. "
                "Your account has been blocked from logging in.",
    2148916238: "The account date of birth is under 18 years and cannot "
                "proceed unless the account is added to a family by an "
                "adult.",
}
