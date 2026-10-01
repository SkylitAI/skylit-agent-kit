"""One explicit, non-retrying GET to Skylit's account endpoint."""

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class AccountError(ValueError):
    """A sanitized account lookup failure, safe to show in a terminal."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def reject_constant(value):
    raise ValueError("Non-finite JSON number")


def read_account(api_key):
    if not isinstance(api_key, str) or not re.fullmatch(r"[!-~]{1,4096}", api_key):
        raise AccountError("Set SKYLIT_API_KEY to your key in the process environment; do not paste it in a prompt.")
    request = Request(
        "https://api.skylit.ai/v1/account",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json", "User-Agent": "skylit-agent-kit/0.1-dev"},
        method="GET",
    )
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            body = response.read(1048577)
    except HTTPError as error:
        error.close()
        guidance = {
            401: "Check or rotate the credential.",
            402: "Check credits and account access.",
            403: "Check entitlements and account access.",
            429: "Rate limited; wait before a later manual attempt.",
            503: "Service unavailable; try manually later.",
        }.get(error.code, "Check the official service documentation.")
        raise AccountError(f"Account request stopped (HTTP {error.code}). {guidance} No retry was sent.") from None
    except (URLError, OSError):
        raise AccountError("Connection failed. Check connectivity and TLS; no retry was sent.") from None
    if len(body) > 1048576:
        raise AccountError("Account response exceeded 1 MiB.")
    try:
        result = json.loads(body, parse_constant=reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise AccountError("Account returned invalid JSON.") from None
    if not isinstance(result, dict):
        raise AccountError("Account returned an unexpected response shape.")
    return result
