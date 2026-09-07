"""
otel_oauth - authenticate OTLP exports to the collector against Keycloak
using an OAuth2 client-credentials grant.

Why this exists
----------------
The OTLP HTTP exporters have no built-in OAuth support - only a static
`headers` dict set once at construction. A Keycloak-issued access token is
short-lived (5 minutes for the local realm), so a header fixed at startup
would go stale and every export would start failing with 401 partway through
the process's life.

What it actually does
----------------------
`ClientCredentialsAuth` is a `requests.auth.AuthBase`: passed as a Session's
`auth`, it runs on every outgoing request, not just once. It fetches a token
via the client_credentials grant on first use, caches it, and transparently
re-fetches shortly before it expires - so the exporters' HTTP sessions always
carry a currently-valid `Authorization: Bearer <token>` header without the
exporter code needing to know anything about OAuth.

Configuration
-------------
Opt-in: if OTEL_OAUTH_ENABLED is false, or OTEL_OAUTH_CLIENT_ID or
OTEL_OAUTH_TOKEN_ENDPOINT_URL is unset, `build_auth()` returns None and the
exporters run without an Authorization header at all, exactly as before this
module existed.

The client secret is OTEL_OAUTH_CLIENT_SECRET (or, preferably,
OTEL_OAUTH_CLIENT_SECRET_FILE pointing at a mounted secret) - a dedicated
Keycloak credential for the dpn-service-client client. It is NOT the Azure
Service Principal's CLIENT_SECRET: an earlier version of this module reused
that value, which mixed two unrelated trust domains (Azure AD, Keycloak)
under one shared secret. That has since been corrected; each OAuth consumer
now holds its own credential.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests
from requests.auth import AuthBase

from app.config.settings import Settings

_LOG = logging.getLogger(__name__)

# Refetch this many seconds before actual expiry, so a request in flight
# never races a token that expires mid-request.
_EXPIRY_SAFETY_MARGIN_SECONDS = 30


class TokenFetchError(RuntimeError):
    """Raised when the client-credentials grant itself fails.

    Deliberately fatal rather than silently exporting without a token: once
    OAuth has been configured, a producer that cannot authenticate should
    stop rather than quietly send unauthenticated telemetry that a
    token-enforcing collector would then reject anyway.
    """


class ClientCredentialsAuth(AuthBase):
    """requests auth plugin: attaches a live OAuth2 client-credentials token.

    Shared across the trace/metric/log exporters' Sessions (one instance, one
    token cache) so three background export threads don't each fetch their
    own token independently. A lock guards the refresh so concurrent callers
    from those threads see one fetch, not three.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        verify: "bool | str" = True,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._verify = verify

        self._lock = threading.Lock()
        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def _fetch_token(self) -> None:
        try:
            response = requests.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                verify=self._verify,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise TokenFetchError(
                f"could not obtain an OAuth token from {self._token_url}: {exc}"
            ) from exc

        token = payload.get("access_token")
        if not token:
            raise TokenFetchError(
                f"token endpoint {self._token_url} did not return an access_token"
            )

        expires_in = payload.get("expires_in", 60)

        self._token = token
        self._expires_at = time.monotonic() + expires_in - _EXPIRY_SAFETY_MARGIN_SECONDS

        _LOG.info(
            "Obtained OAuth token from %s (expires in %ss)",
            self._token_url,
            expires_in,
        )

    def _current_token(self) -> str:
        with self._lock:
            if self._token is None or time.monotonic() >= self._expires_at:
                self._fetch_token()
            return self._token

    def __call__(self, request):
        request.headers["Authorization"] = f"Bearer {self._current_token()}"
        return request


def _resolve_client_secret() -> Optional[str]:
    """Return the OAuth client secret: a mounted file wins over the raw env var."""
    secret_file = Settings.OTEL_OAUTH_CLIENT_SECRET_FILE

    if secret_file:
        try:
            with open(secret_file, "r", encoding="utf-8") as handle:
                return handle.read().strip()
        except OSError as exc:
            raise TokenFetchError(
                f"OTEL_OAUTH_CLIENT_SECRET_FILE is set to {secret_file} but it "
                f"could not be read: {exc}"
            ) from exc

    return Settings.OTEL_OAUTH_CLIENT_SECRET


def build_auth(verify: "bool | str" = True) -> Optional[ClientCredentialsAuth]:
    """Return a ClientCredentialsAuth, or None if OAuth is not configured.

    *verify* is the fallback TLS verification target for the token endpoint
    (normally the same CA certificate used for the OTLP exporters, since
    Keycloak's cert here is signed by the same CA) - overridden by
    OTEL_OAUTH_CA_LOCATION when that is set.
    """
    if not Settings.OTEL_OAUTH_ENABLED:
        return None

    token_url = Settings.OTEL_OAUTH_TOKEN_ENDPOINT_URL
    client_id = Settings.OTEL_OAUTH_CLIENT_ID

    if not token_url or not client_id:
        return None

    client_secret = _resolve_client_secret()

    if not client_secret:
        raise TokenFetchError(
            "OTEL_OAUTH_CLIENT_ID/OTEL_OAUTH_TOKEN_ENDPOINT_URL are set but "
            "neither OTEL_OAUTH_CLIENT_SECRET nor OTEL_OAUTH_CLIENT_SECRET_FILE "
            "is; OAuth cannot be configured without a secret."
        )

    ca_location = Settings.OTEL_OAUTH_CA_LOCATION or verify

    return ClientCredentialsAuth(token_url, client_id, client_secret, verify=ca_location)
