from app.providers.azure.servicebus_client import (
    get_receiver
)

from app.providers.azure.processor import (
    process_message
)


def start_listener():

    receiver = get_receiver()

    with receiver:

        while True:

            messages = receiver.receive_messages(
                max_message_count=10,
                max_wait_time=5
            )

            for message in messages:

                try:

                    process_message(message)

                    """ receiver.complete_message(
                        message
                    )
 """
                except Exception as ex:

                    print(ex)

                    """ receiver.abandon_message(
                        message
                    ) """
 