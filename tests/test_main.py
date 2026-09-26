from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient

from app.main import app, lifespan
import app.main as main

client = TestClient(app)


def test_app_created():

    assert app.title == "File Scan App"

    assert app.version == "1.0.0"


def test_health():

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {"status": "UP"}


def test_version():

    response = client.get("/version")

    assert response.status_code == 200

    assert response.json() == {"application": "file-scan-app", "version": "1.0.0"}


@pytest.mark.asyncio
async def test_lifespan_azure():

    with (
        patch("app.main.configure_telemetry"),
        patch("app.main.Settings.CLOUD_PROVIDER_TYPE", "AZURE"),
        patch("threading.Thread") as mock_thread,
    ):
        async with lifespan(None):
            # entering the context runs startup, which spawns the listener
            pass

        mock_thread.assert_any_call(
            target=main.start_azure_listener,
            daemon=True,
            name="servicebus-listener",
        )


@pytest.mark.asyncio
async def test_lifespan_s3():

    with (
            patch("app.main.configure_telemetry"),
            patch("app.main.Settings.CLOUD_PROVIDER_TYPE", "AWS"),
            patch("threading.Thread") as mock_thread,
        ):

            async with lifespan(None):
                # entering the context runs startup, which spawns the listener
                pass

            mock_thread.assert_any_call(
                target=main.start_aws_listener,
                daemon=True,
                name="sqs-listener",
            )


@pytest.mark.asyncio
async def test_lifespan_gcp():

    with (
        patch("app.main.configure_telemetry"),
        patch("app.main.Settings.CLOUD_PROVIDER_TYPE", "GCP"),
    ):

        with patch.dict("sys.modules", {"app.providers.gcp.processor": MagicMock()}):

            async with lifespan(None):
                # startup selects the GCP provider without raising
                pass


@pytest.mark.asyncio
async def test_lifespan_invalid_provider():

    with (
        patch("app.main.configure_telemetry"),
        patch("app.main.Settings.CLOUD_PROVIDER_TYPE", "UNKNOWN"),
    ):

        with pytest.raises(ValueError):

            async with lifespan(None):
                # startup must reject an unknown provider
                pass
