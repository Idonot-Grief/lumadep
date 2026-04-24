# -*- coding: utf-8 -*-
"""
Microsoft / Xbox Live authentication using MSAL device-code flow.

No redirect URI registration needed.  The user is shown a short code and
a URL (login.microsoftonline.com/common/oauth2/deviceauth); they enter the
code in any browser and the launcher polls until it is approved.

Requires:  pip install msal requests
"""
import json
import webbrowser

try:
    import msal
except ImportError:
    msal = None

try:
    import requests
except ImportError:
    requests = None

from .config import load_config, save_config

# Azure app registration for the official Minecraft launcher (public client)
# This client supports the device-code flow without a secret.
_CLIENT_ID = "389b1b32-b5d5-43b2-bddc-84ce938d6737"
_AUTHORITY  = "https://login.microsoftonline.com/consumers"
_SCOPES     = ["XboxLive.signin", "offline_access"]

XBOX_AUTH_URL  = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_AUTH_URL  = "https://xsts.auth.xboxlive.com/xsts/authorize"
MC_LOGIN_URL   = "https://api.minecraftservices.com/authentication/login_with_xbox"
MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"


def _get_msal_app():
    if msal is None:
        raise RuntimeError(
            "msal is not installed. Run:  pip install msal"
        )
    return msal.PublicClientApplication(_CLIENT_ID, authority=_AUTHORITY)


def microsoft_login(progress_cb=None):
    """
    Authenticate via MSAL device-code flow and return the Minecraft username.

    progress_cb(message: str) is called with status updates if provided.
    A dialog / print statement can be wired up by the caller.
    """
    if requests is None:
        raise RuntimeError("requests is not installed. Run:  pip install requests")

    def _prog(msg):
        if progress_cb:
            progress_cb(msg)

    app = _get_msal_app()

    # Try silent refresh first
    accounts = app.get_accounts()
    result = None
    if accounts:
        _prog("Trying silent token refresh...")
        result = app.acquire_token_silent(_SCOPES, account=accounts[0])

    if not result:
        _prog("Starting device-code login...")
        flow = app.initiate_device_flow(scopes=_SCOPES)
        if "user_code" not in flow:
            raise RuntimeError("Failed to start device-code flow: " + str(flow))

        # Show the user the URL + code
        msg = (
            "To sign in, open this URL in your browser:
"
            "  {url}

"
            "Then enter this code:  {code}

"
            "Waiting for you to complete login (up to 15 minutes)..."
        ).format(url=flow["verification_uri"], code=flow["user_code"])
        _prog(msg)
        webbrowser.open(flow["verification_uri"])

        result = app.acquire_token_by_device_flow(flow)  # blocks until done

    if "error" in result:
        raise RuntimeError(
            "Microsoft login failed: {err} - {desc}".format(
                err=result.get("error", ""),
                desc=result.get("error_description", "")
            )
        )

    ms_access  = result["access_token"]
    ms_refresh = result.get("refresh_token", "")

    _prog("Authenticating with Xbox Live...")

    # Xbox Live
    xbox_resp = requests.post(XBOX_AUTH_URL, json={
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName":   "user.auth.xboxlive.com",
            "RpsTicket":  "d=" + ms_access,
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType":    "JWT",
    }, timeout=30)
    xbox_resp.raise_for_status()
    xbox_token = xbox_resp.json()["Token"]

    # XSTS
    xsts_resp = requests.post(XSTS_AUTH_URL, json={
        "Properties": {
            "SandboxId":  "RETAIL",
            "UserTokens": [xbox_token],
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType":    "JWT",
    }, timeout=30)
    xsts_resp.raise_for_status()
    xsts_body  = xsts_resp.json()
    xsts_token = xsts_body["Token"]
    uhs        = xsts_body["DisplayClaims"]["xui"][0]["uhs"]

    _prog("Logging in to Minecraft...")

    # Minecraft login
    mc_resp = requests.post(MC_LOGIN_URL, json={
        "identityToken": "XBL3.0 x={uhs};{xsts}".format(uhs=uhs, xsts=xsts_token)
    }, timeout=30)
    mc_resp.raise_for_status()
    mc_token = mc_resp.json()["access_token"]

    # Profile
    profile_resp = requests.get(
        MC_PROFILE_URL,
        headers={"Authorization": "Bearer " + mc_token},
        timeout=30,
    )
    profile_resp.raise_for_status()
    profile = profile_resp.json()

    # Save
    config = load_config()
    config.auth.offline_mode          = False
    config.auth.use_microsoft_account = True
    config.auth.access_token          = mc_token
    config.auth.refresh_token         = ms_refresh
    config.auth.username              = profile["name"]
    config.auth.uuid                  = profile["id"]
    save_config(config)

    _prog("Signed in as " + profile["name"])
    return profile["name"]


def get_minecraft_token():
    """Return the stored Minecraft access token, or None if offline."""
    config = load_config()
    if config.auth.offline_mode:
        return None
    return config.auth.access_token or None
