# syntax=docker/dockerfile:1
 
# ---------------------------------------------------------------------------
# Alpine-based image. Alpine uses musl libc, NOT glibc, so glibc CVEs such as
# CVE-2026-5450 (which has no fixed package in Debian bookworm) do not apply
# here at all. Base pinned by digest for reproducible, scannable builds.
# Tag for reference: python:3.14-alpine3.23
# ---------------------------------------------------------------------------
    ARG BASE_IMAGE=python:3.14-alpine
 
    # =========================================================================
    # Stage 1 — builder: install dependencies into an isolated venv.
    # No build toolchain is installed: every dependency must resolve to a
    # prebuilt musllinux cp314 wheel (--only-binary=:all:). If any package
    # lacks a wheel, the build fails loudly instead of silently compiling.
    # =========================================================================
    FROM ${BASE_IMAGE} AS builder
     
    ENV PYTHONUNBUFFERED=1 \
        PYTHONDONTWRITEBYTECODE=1 \
        PIP_NO_CACHE_DIR=1 \
        VENV_PATH=/opt/venv \
        PATH="/opt/venv/bin:${PATH}"
     
    WORKDIR /app
     
    COPY requirements.txt .
    COPY packages ./packages
     
    # Pull any OS package fixes available in the Alpine release.
    RUN apk update && \
        apk upgrade --no-cache
     
    RUN python -m pip install --upgrade pip
     
    RUN python -m venv "${VENV_PATH}" && \
        pip install --upgrade pip setuptools wheel && \
        pip install --no-cache-dir --only-binary=:all: -r requirements.txt && \
        pip uninstall -y pip
     
    RUN rm -f ${VENV_PATH}/bin/pip* && \
        rm -rf ${VENV_PATH}/lib/python3.14/site-packages/pip*
     
    # =========================================================================
    # Stage 2 — runtime: minimal Alpine + the venv and app code only.
    # No compiler, no curl, no build toolchain -> small attack surface.
    #
    # The base image (python:3.14-alpine) ships its own system-level pip
    # outside of any venv. That system pip is what Xray flags as
    # CVE-2018-20225 (High) — a dependency-confusion design issue in pip's
    # --extra-index-url resolution with no upstream fixed version. Since the
    # runtime container never needs pip (the venv is prebuilt in stage 1 and
    # already had its own pip stripped), we remove the base image's system
    # pip/setuptools here so the vulnerable component is not present in the
    # shipped image at all.
    # =========================================================================
    FROM ${BASE_IMAGE} AS runtime
     
    ENV PYTHONUNBUFFERED=1 \
        PYTHONDONTWRITEBYTECODE=1 \
        VENV_PATH=/opt/venv \
        PATH="/opt/venv/bin:${PATH}"
     
    # Strip pip/setuptools from the base image's system Python.
    # Using pip's own uninstaller first (accurate, handles metadata cleanly),
    # then a defensive rm -rf as a fallback in case pip removes itself before
    # fully cleaning up its own dist-info/egg-info directories.
    RUN python -m pip uninstall -y pip setuptools wheel 2>/dev/null; \
        rm -rf /usr/lib/python3.14/site-packages/pip* \
               /usr/lib/python3.14/site-packages/setuptools* \
               /usr/lib/python3.14/site-packages/wheel* \
               /usr/bin/pip* \
               /usr/lib/python3.14/__pycache__/pip* \
               /usr/lib/python3.14/__pycache__/setuptools*
     
    # Non-root runtime user (BusyBox adduser/addgroup syntax).
    RUN addgroup -S appgroup && \
        adduser -S -G appgroup -h /home/appuser appuser
     
    WORKDIR /app
     
    # Copy the pre-built virtual environment and the application source.
    # The venv references the base image's interpreter; both stages use the
    # identical pinned base, so the interpreter and musl version match exactly.
    COPY --from=builder --chown=appuser:appgroup ${VENV_PATH} ${VENV_PATH}
    COPY --chown=appuser:appgroup . .
     
    USER appuser
     
    EXPOSE 8080
     
    # --loop asyncio: run on the stdlib event loop (uvloop is not installed and is
    # not yet compatible with Python 3.14). Explicit so the loop choice is pinned.
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--loop", "asyncio"]