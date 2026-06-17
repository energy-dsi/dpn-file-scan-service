from app.config.settings import Settings


def start():

    if Settings.CLOUD_PROVIDER_TYPE == "AZURE":

        from app.main import main

        main()

    elif Settings.CLOUD_PROVIDER_TYPE == "S3":

        from app.providers.aws.processor \
            import process

        process()

    elif Settings.CLOUD_PROVIDER_TYPE == "GCP":

        from app.providers.gcp.processor \
            import process

        process()

    else:

        raise ValueError(
            "Unsupported Provider"
        )