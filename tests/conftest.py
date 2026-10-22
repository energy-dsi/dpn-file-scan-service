import pytest


@pytest.fixture
def clean_message():

    return {"fileName": "invoice.pdf", "scanResult": "OK"}


@pytest.fixture
def malicious_message():

    return {"fileName": "virus.exe", "scanResult": "MALICIOUS"}
