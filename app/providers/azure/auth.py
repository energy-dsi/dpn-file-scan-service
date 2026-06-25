from azure.identity import ClientSecretCredential

from app.config.settings import Settings


def get_credential():

    return ClientSecretCredential(
        tenant_id=Settings.TENANT_ID,
        client_id=Settings.CLIENT_ID,
        client_secret=Settings.CLIENT_SECRET,
    )
