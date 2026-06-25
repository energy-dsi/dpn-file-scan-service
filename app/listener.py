from app.providers.azure.processor import process_message
from app.providers.azure.servicebus_client import get_receiver


def start_listener():

    receiver = get_receiver()

    with receiver:

        while True:

            messages = receiver.receive_messages(max_message_count=10, max_wait_time=5)

            for message in messages:

                try:

                    print(f"Locked Until: " f"{message.locked_until_utc}")

                    print(f"Delivery Count: " f"{message.delivery_count}")

                    process_message(message)

                    print(f"Completing message: {message.message_id}")

                    try:
                        import time

                        start = time.time()
                        print("Calling complete_message...")

                        receiver.complete_message(message)
                        print(
                            f"complete_message returned in "
                            f"{time.time() - start:.2f} seconds"
                        )

                        print(f"Completed message: {message.message_id}")

                    except Exception as complete_ex:
                        print(f"Complete Failed: " f"{type(complete_ex).__name__}")
                        print(f"ERROR: {complete_ex}")
                        raise

                except Exception as ex:

                    print(f"Process Failed: {ex}")
                    try:
                        receiver.abandon_message(message)
                    except Exception as abandon_ex:
                        print(f"Abandon Failed: " f"{abandon_ex}")
