# Copyright DSI Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
otlp_truststore - take OTLP CA trust from the password-protected PKCS12
truststore, the same file the JVM services consume.

Why this exists
---------------
The DPN PKI ships one trust anchor in two formats:

    dpn-observability-truststore.p12   PKCS12 + password   (Keycloak, Kafka UI)
    rootCA.crt                         PEM                 (Go and Python)

Both hold the identical NESO-DSI-Root-CA certificate. This module makes the
``.p12`` the single distributed artefact for Python producers too: one file to
ship, one password to rotate, and the tamper-evidence a PKCS12 MAC provides.

What it actually does
---------------------
Python has no truststore support at any layer - not ``ssl``, not ``requests``,
not the OTLP exporters - because PKCS12 and JKS are Java container formats.
There is no ``trustStorePassword`` equivalent to set. So this module:

    1. opens the .p12 with the password (``cryptography`` parses PKCS12, which
       the standard library cannot),
    2. writes the CA certificates inside it to a private temporary PEM file,
    3. points ``OTEL_EXPORTER_OTLP_CERTIFICATE`` at that file,
    4. removes it when the process ends.

BE CLEAR ABOUT WHAT THIS DOES AND DOES NOT GIVE YOU. The password is genuinely
required and genuinely verified: a wrong password, or a truststore altered by so
much as one byte, fails at step 1 and the producer never starts. That integrity
guarantee is the real reason to prefer this over the PEM.

What it is NOT is Python "using a truststore" the way a JVM does. The JVM holds
the store and consults it inside its TLS stack; here it is decrypted up front
and Python's TLS stack sees only PEM. A short-lived 0600 copy of a PUBLIC CA
certificate exists on disk while the process runs. That is not a secret - it is
broadcast in every TLS handshake - but it does mean the .p12 is a distribution
and integrity mechanism here, not a runtime one.

Configuration
-------------
Deliberately NONE. The location and password are the hardcoded constants below,
matching how the rest of the DPN stack pins them (Keycloak's
KC_HTTPS_TRUST_STORE_PASSWORD, Kafka UI's -Djavax.net.ssl.trustStorePassword,
and P12_PASS in config/certs/generate-certs.sh are all the literal "changeit").
Nothing needs to be set per producer; ``otlp_transport`` calls ``configure()``
before it builds any exporter.

If no truststore is found at any known path this is a silent no-op, so a
producer configured the plain way - OTEL_EXPORTER_OTLP_CERTIFICATE pointing at
rootCA.crt - keeps working untouched.
"""

from __future__ import annotations

import atexit
import logging
import os
import signal
import tempfile
from typing import Optional
from app.config.settings import Settings

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Truststore location.
#
# A single literal path cannot cover both cases: inside a container the PKI is
# bind-mounted at /certs (every service in docker-compose.observability-full.yml
# mounts ../../certs/dpn-observability there), while a developer running a
# producer directly on Windows has it under the checkout's sibling certs dir.
# So this is an ordered list of candidates and the first one that exists wins.
#
# TRUSTSTORE_PATH (env, via Settings) REPLACES the hardcoded defaults below
# when set, so a deployment shape that puts the store somewhere else (a
# different mount point, a Kubernetes projected volume, etc.) can be pointed
# at it without a code change, with no hardcoded fallback still being tried.
# It accepts one or more paths separated by os.pathsep, tried in order.
# Existing deployments that set nothing keep using the hardcoded defaults
# unchanged.
# ---------------------------------------------------------------------------
# Repo root: this file is <repo>/app/telemetry/otel_truststore.py, so three
# dirname() hops from its absolute path land on <repo> (file-scan-app).
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

_DEFAULT_TRUSTSTORE_PATHS = (
    # Container: docker-compose.yml bind-mounts ./.certs -> /certs:ro, so a
    # truststore dropped into the repo's .certs/ dir appears here. The only
    # entry that matters in a deployed producer.
    "/certs/dpn-observability-truststore.p12",
    # Local development on the host: the repo's own .certs/ directory (same dir
    # that already holds rootCA.crt for the plain PEM path).
    os.path.join(_REPO_ROOT, ".certs", "dpn-observability-truststore.p12"),
)


def _build_truststore_paths() -> tuple[str, ...]:
    """Env override(s) if set, replacing the hardcoded defaults entirely."""
    override = (Settings.TRUSTSTORE_PATH or "").strip()
    if not override:
        return _DEFAULT_TRUSTSTORE_PATHS

    return tuple(p.strip() for p in override.split(os.pathsep) if p.strip())


TRUSTSTORE_PATHS = _build_truststore_paths()

# Matches P12_PASS in config/certs/generate-certs.sh, which is what the stores
# are actually built with. Changing it here alone achieves nothing - the .p12 is
# already encrypted with the old value, so the PKI has to be regenerated too.
#
# Safe to keep in source for this PKI: a TRUSTSTORE password protects the file's
# integrity (tamper detection), not its confidentiality - everything inside is a
# public CA certificate that every TLS handshake broadcasts anyway. Do NOT copy
# this posture to a keystore, which holds a private key.
TRUSTSTORE_PASSWORD = Settings.TRUSTSTORE_PASSWORD
# The OpenTelemetry spec variable the exporters read the CA path out of. This is
# an OUTPUT - what this module sets - not a knob, so it is spelled out here
# rather than being configurable.
ENV_CERTIFICATE = "OTEL_EXPORTER_OTLP_CERTIFICATE"

# Set once configure() has materialised a PEM, so the three exporters (logs,
# traces, metrics) reuse one file rather than decrypting three times and
# leaking two of them.
_extracted_pem: Optional[str] = None


class TruststoreError(RuntimeError):
    """Raised when a truststore is found but cannot be opened or is unusable.

    Deliberately fatal rather than a warning that falls back to the PEM: once a
    trust anchor has been located, a producer should stop rather than quietly
    switch to a different one.
    """


def _find_truststore() -> Optional[str]:
    """Return the first hardcoded truststore path that exists, or None."""
    for candidate in TRUSTSTORE_PATHS:
        if os.path.isfile(candidate):
            return candidate
    _LOG.debug("no truststore at any of: %s", ", ".join(TRUSTSTORE_PATHS))
    return None


def _load_ca_pem(path: str, password: Optional[str]) -> bytes:
    """Return every certificate in *path* concatenated as PEM."""
    try:
        from cryptography.hazmat.primitives.serialization import Encoding, pkcs12
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise TruststoreError(
            f"found truststore {path} but the 'cryptography' package is not "
            "installed; it is required to read PKCS12 from Python"
        ) from exc

    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise TruststoreError(f"cannot read truststore {path}: {exc}") from exc

    # An empty password is NOT the same as no password: load_pkcs12 wants None
    # for a store built without one, and b"" fails against it.
    secret = password.encode() if password else None

    try:
        bundle = pkcs12.load_pkcs12(raw, secret)
    except ValueError as exc:
        # cryptography reports a wrong password and a tampered file through the
        # same ValueError - from the MAC failure alone they are genuinely
        # indistinguishable, so name both possibilities.
        raise TruststoreError(
            f"could not open truststore {path}: {exc}. Either TRUSTSTORE_PASSWORD "
            "in this module no longer matches P12_PASS in "
            "config/certs/generate-certs.sh, or the file has been altered since "
            "it was created (a PKCS12 MAC covers the whole file)."
        ) from exc

    # A truststore holds trustedCertEntry items only, which land in
    # additional_certs. bundle.cert is the entry paired with a private key and
    # is None here - unless someone passed a KEYSTORE by mistake, so take it too
    # rather than silently producing an empty PEM.
    certs = [entry.certificate for entry in bundle.additional_certs]
    if bundle.cert is not None:
        certs.append(bundle.cert.certificate)

    if not certs:
        raise TruststoreError(
            f"truststore {path} opened successfully but contains no certificates"
        )

    _LOG.debug("loaded %d certificate(s) from %s", len(certs), path)
    return b"".join(cert.public_bytes(Encoding.PEM) for cert in certs)


def configure() -> Optional[str]:
    """Point OTLP CA trust at the PKCS12 truststore, if one is present.

    Returns the path of the extracted PEM, or None when no truststore was found
    at any hardcoded location. Safe to call repeatedly.
    """
    global _extracted_pem

    if _extracted_pem is not None:
        return _extracted_pem

    truststore = _find_truststore()
    if truststore is None:
        return None

    existing = (os.getenv(ENV_CERTIFICATE) or "").strip()
    if existing:
        # Both present is ambiguous about which anchor wins, and the exporters
        # read ENV_CERTIFICATE themselves - so say which one is being used
        # rather than letting it depend on import order.
        _LOG.warning(
            "truststore %s found and %s is also set; the truststore takes "
            "precedence and %s will be overwritten",
            truststore, ENV_CERTIFICATE, ENV_CERTIFICATE,
        )

    pem = _load_ca_pem(truststore, TRUSTSTORE_PASSWORD)

    # mkstemp gives 0600 and an O_EXCL create, so no other user on the host can
    # read or pre-create the file. The contents are a public CA, but the PATH is
    # what the TLS stack trusts - a world-writable one would be swappable.
    fd, pem_path = tempfile.mkstemp(prefix="otlp-ca-", suffix=".pem")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(pem)
    except Exception:
        os.unlink(pem_path)
        raise

    _install_cleanup(pem_path)

    os.environ[ENV_CERTIFICATE] = pem_path
    _extracted_pem = pem_path

    _LOG.info("OTLP CA trust taken from truststore %s", truststore)
    return pem_path


def _install_cleanup(path: str) -> None:
    """Arrange for *path* to be removed however this process ends.

    atexit ALONE IS NOT ENOUGH. It runs on a normal interpreter exit, but not
    when the process is signalled - and SIGTERM is precisely how a container is
    stopped, so a pod that restarts nightly would leave one stale PEM behind per
    restart. Chain a handler onto SIGTERM/SIGINT that cleans up and then lets the
    previous behaviour run, so we tidy up without swallowing the shutdown.
    """
    atexit.register(_cleanup, path)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            previous = signal.getsignal(sig)
        except (ValueError, OSError, AttributeError):  # pragma: no cover
            continue

        def handler(signum, frame, _previous=previous, _path=path):
            _cleanup(_path)
            if callable(_previous):
                _previous(signum, frame)
            else:
                # SIG_DFL / SIG_IGN: restore it and re-raise so the process dies
                # with the right status instead of silently continuing.
                signal.signal(signum, signal.SIG_DFL)
                os.kill(os.getpid(), signum)

        try:
            signal.signal(sig, handler)
        except (ValueError, OSError, AttributeError):
            # signal.signal only works on the main thread, and Windows delivers
            # a narrower set. Not fatal - atexit still covers the normal path,
            # and the file holds a public certificate, so a leak on a hard kill
            # is untidy rather than a disclosure.
            _LOG.debug("could not install %s cleanup handler", sig, exc_info=True)


def _cleanup(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:  # already gone, or the temp dir was cleared under us
        pass
 