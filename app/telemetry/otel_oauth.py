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

OTEL_OAUTH_CA_LOCATION (the CA used to verify the token endpoint's own TLS
certificate) accepts a plain PEM file OR a .jks truststore - `requests`
cannot read JKS (or PKCS#12) directly, so a .jks path is detected by
extension and extracted to a temporary PEM first (see
_materialise_jks_as_pem). The JKS password is TRUSTSTORE_PASSWORD, the same
password the rest of the DPN PKI is built with.

The client secret is OTEL_OAUTH_CLIENT_SECRET (or, preferably,
OTEL_OAUTH_CLIENT_SECRET_FILE pointing at a mounted secret) - a dedicated
Keycloak credential for the dpn-service-client client. It is NOT the Azure
Service Principal's CLIENT_SECRET: an earlier version of this module reused
that value, which mixed two unrelated trust domains (Azure AD, Keycloak)
under one shared secret. That has since been corrected; each OAuth consumer
now holds its own credential.
"""

from __future__ import annotations

import atexit
import logging
import os
import tempfile
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

    def bearer_header(self) -> dict:
        """Return a fresh {"authorization": "Bearer <token>"} dict.

        For consumers that cannot use this object as a `requests` auth
        callable (e.g. the gRPC exporter, which only takes a static headers
        dict/tuple at construction time - it never calls back into this
        object per-request the way `requests.Session.auth` does). Unlike
        __call__, which is invoked fresh on every HTTP request, a header
        fetched this way is fixed for the lifetime of whatever it is attached
        to and will NOT be refreshed before it expires.

        Lowercase key deliberately: gRPC metadata keys must be lowercase
        ASCII (grpc-core rejects "Authorization" outright with "Illegal
        header key"), unlike HTTP header names, which are case-insensitive.
        """
        return {"authorization": f"Bearer {self._current_token()}"}


def _extract_jks_ca_pem(path: str, password: Optional[str]) -> bytes:
    """Return every trusted certificate in a JKS truststore as PEM bytes.

    `requests`' `verify=` can only read a PEM CA bundle - it cannot parse JKS
    any more than it could parse PKCS#12 (see the module docstring for the
    OTEL_OAUTH_CA_LOCATION=.p12 failure this was written to fix). `pyjks` (the
    only Python library that reads the JKS binary format) is used to open the
    store and pull out its trustedCertEntry items only - no private key
    material is ever touched, since this is a truststore, not a keystore.
    """
    try:
        import jks
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise TokenFetchError(
            f"OTEL_OAUTH_CA_LOCATION {path} is a .jks file but the 'pyjks' "
            "package is not installed; it is required to read JKS from Python"
        ) from exc

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives.serialization import Encoding
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise TokenFetchError(
            f"OTEL_OAUTH_CA_LOCATION {path} is a .jks file but the "
            "'cryptography' package is not installed; it is required to "
            "convert JKS certificates to PEM"
        ) from exc

    try:
        keystore = jks.KeyStore.load(path, password or "")
    except Exception as exc:
        raise TokenFetchError(
            f"could not open JKS truststore {path}: {exc}. Either the "
            "password (TRUSTSTORE_PASSWORD) does not match the password "
            "the store was built with, or the file has been altered since "
            "it was created (JKS covers the whole store with an integrity "
            "hash)."
        ) from exc

    certs = [
        x509.load_der_x509_certificate(entry.cert)
        for entry in keystore.certs.values()
    ]

    if not certs:
        raise TokenFetchError(
            f"JKS truststore {path} opened successfully but contains no "
            "certificates"
        )

    return b"".join(cert.public_bytes(Encoding.PEM) for cert in certs)


def _materialise_jks_as_pem(path: str) -> str:
    """Extract *path* (a .jks file) to a temporary PEM and return its path.

    Reuses TRUSTSTORE_PASSWORD - the same password the rest of the DPN stack
    (Keycloak's KC_HTTPS_TRUST_STORE_PASSWORD, Kafka UI's
    -Djavax.net.ssl.trustStorePassword) is built with, rather than inventing
    a second OAuth-specific password setting for what is the same PKI. The
    temp file is cleaned up at interpreter exit; its contents are a public CA,
    so a leak on a hard kill is untidy rather than a disclosure.
    """
    pem = _extract_jks_ca_pem(path, Settings.TRUSTSTORE_PASSWORD)

    fd, pem_path = tempfile.mkstemp(prefix="oauth-ca-", suffix=".pem")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(pem)
    except Exception:
        os.unlink(pem_path)
        raise

    atexit.register(lambda: os.path.exists(pem_path) and os.unlink(pem_path))

    _LOG.info("OAuth token-endpoint CA trust taken from JKS truststore %s", path)
    return pem_path


def _resolve_ca_verify(ca_location, fallback: "bool | str"):
    """Return the *verify* value for the token endpoint's TLS check.

    A .jks CA location is extracted to a temporary PEM first, since
    `requests` cannot read JKS directly; anything else (a PEM path, or
    nothing at all) is passed through unchanged.
    """
    if ca_location and str(ca_location).lower().endswith(".jks"):
        return _materialise_jks_as_pem(ca_location)

    return ca_location or fallback


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

    ca_verify = _resolve_ca_verify(Settings.OTEL_OAUTH_CA_LOCATION, verify)

    return ClientCredentialsAuth(token_url, client_id, client_secret, verify=ca_verify)


def bearer_header_tuple(
    auth: Optional[ClientCredentialsAuth],
) -> "tuple[tuple[str, str], ...]":
    """Return a gRPC-exporter-shaped headers tuple, or empty when auth is None.

    Fetches the token once, immediately - see ClientCredentialsAuth.bearer_header
    for why this is a one-shot value rather than a live-refreshing one.
    """
    if auth is None:
        return ()

    header = auth.bearer_header()
    return tuple(header.items())
