import time

from src.kafka_producer import create_producer, send_aircraft_records
from src.opensky_client import fetch_aircraft_states


def poll_and_publish(interval_seconds=300, cycles=None):
    producer = create_producer()

    try:
        cycle = 0

        while cycles is None or cycle < cycles:
            cycle += 1

            print(f"Polling cycle {cycle}")

            records = fetch_aircraft_states()

            print(f"Collected {len(records)} aircraft records")

            if records:
                send_aircraft_records(producer, records)
                print("Aircraft records sent to Kafka")

            print(f"Waiting {interval_seconds} seconds...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nPolling stopped by user.")

    finally:
        producer.close()
        print("Kafka producer closed.")


if __name__ == "__main__":
    poll_and_publish(
        interval_seconds=300,
        cycles=None
    )