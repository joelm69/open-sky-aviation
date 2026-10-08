import json

from google.cloud import storage
from kafka import KafkaConsumer, TopicPartition


TOPIC = "aircraft-states"
CONSUMER_GROUP = "opensky-gcs-test"
BUCKET_NAME = "open-sky-aviation-raw"


def create_consumer():
    """Create a Kafka consumer using the existing consumer group."""

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers="localhost:9092",
        group_id=CONSUMER_GROUP,
        enable_auto_commit=False,
        value_deserializer=lambda value: (
            json.loads(value.decode("utf-8"))
            if value
            else None
        ),
    )

    return consumer


def create_storage_client():
    """Create a Google Cloud Storage client."""

    return storage.Client(project="open-sky-aviation")


def collect_snapshot(consumer):
    """
    Collect one complete snapshot from Kafka.

    When the next snapshot is encountered, move the consumer position
    back to that message so it can be processed on the next iteration.
    """

    current_snapshot_id = None
    snapshot_records = []

    while True:
        messages = consumer.poll(timeout_ms=2000)

        if not messages:
            break

        for topic_partition, records in messages.items():

            for message in records:
                record = message.value

                if record is None:
                    continue

                snapshot_id = record["snapshot_id"]

                if current_snapshot_id is None:
                    current_snapshot_id = snapshot_id

                if snapshot_id != current_snapshot_id:
                    # We have already fetched the first message
                    # belonging to the next snapshot.
                    #
                    # Put the consumer position back so that message
                    # will be processed during the next iteration.
                    consumer.seek(
                        topic_partition,
                        message.offset,
                    )

                    return current_snapshot_id, snapshot_records

                snapshot_records.append(record)

    return current_snapshot_id, snapshot_records


def upload_snapshot(storage_client, snapshot_id, records):
    """Upload one completed snapshot to Google Cloud Storage."""

    if not records:
        return False

    bucket = storage_client.bucket(BUCKET_NAME)

    snapshot = {
        "snapshot_id": snapshot_id,
        "collected_at": records[0]["collected_at"],
        "aircraft": records,
    }

    object_name = f"raw/aircraft_states_{snapshot_id}.json"

    blob = bucket.blob(object_name)

    blob.upload_from_string(
        json.dumps(snapshot),
        content_type="application/json",
    )

    print("Snapshot uploaded to GCS:")
    print(f"gs://{BUCKET_NAME}/{object_name}")

    return True


def process_snapshots(consumer, storage_client):
    """Process Kafka snapshots until the backlog is exhausted."""

    while True:

        snapshot_id, records = collect_snapshot(consumer)

        if not records:
            print("No more complete snapshots available.")
            break

        print()
        print("Snapshot ID:", snapshot_id)
        print("Records collected:", len(records))

        upload_successful = upload_snapshot(
            storage_client,
            snapshot_id,
            records,
        )

        if not upload_successful:
            print("GCS upload failed. Kafka offset will not be committed.")
            break

        # GCS upload succeeded.
        #
        # Commit the current Kafka position. Because collect_snapshot()
        # seeks back to the first message of the next snapshot, the
        # current consumer position is exactly where the next iteration
        # should begin.
        consumer.commit()

        print("Kafka offset committed.")
        print("Snapshot processing complete.")


if __name__ == "__main__":
    consumer = create_consumer()
    storage_client = create_storage_client()

    try:
        process_snapshots(
            consumer,
            storage_client,
        )

    finally:
        consumer.close()
        print("Kafka consumer closed.")