from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {"status": "UP"}


def test_version():

    response = client.get("/version")

    assert response.status_code == 200


@patch("app.api.routes.list_blobs")
def test_outbound_files(mock_list):

    mock_list.return_value = ["a.txt", "b.txt"]

    response = client.get("/outbound/files")

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 2

    assert body["files"] == ["a.txt", "b.txt"]


@patch("app.api.routes.list_blobs")
def test_inbound_files(mock_list):

    mock_list.return_value = ["x.xml"]

    response = client.get("/inbound/files")

    assert response.status_code == 200

    assert response.json()["count"] == 1


@patch("app.api.routes.peek_messages")
def test_servicebus_messages(mock_peek):

    mock_peek.return_value = [{"id": "123"}]

    response = client.get("/servicebus/messages")

    assert response.status_code == 200

    assert response.json()[0]["id"] == "123"


@patch("app.api.routes.list_blobs")
def test_outbound_exception(mock_list):

    mock_list.side_effect = Exception("Storage error")

    response = client.get("/outbound/files")

    assert response.status_code == 500

    assert response.json()["detail"] == "Storage error"


@patch("app.api.routes.list_blobs")
def test_inbound_exception(mock_list):

    mock_list.side_effect = Exception("Storage error")

    response = client.get("/inbound/files")

    assert response.status_code == 500

    assert response.json()["detail"] == "Storage error"
