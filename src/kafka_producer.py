import json
from datetime import datetime

from kafka import KafkaProducer

from src.opensky_client import fetch_aircraft_states


def serialize_json(value):
    def convert_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

        raise TypeError(
            f"Object of type {type(obj).__name__} is not JSON serializable"
        )

    return json.dumps(
        value,
        default=convert_datetime
    ).encode("utf-8")


def create_producer():
    producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=serialize_json,
    )

    return producer


def send_aircraft_records(producer, records):
    for aircraft in records:
        producer.send(
            "aircraft-states",
            aircraft
        )

    producer.flush()


if __name__ == "__main__":
    producer = create_producer()

    aircraft_records = fetch_aircraft_states()

    print(f"Fetched {len(aircraft_records)} aircraft records")

    send_aircraft_records(
        producer,
        aircraft_records
    )

    print("Aircraft records sent to Kafka")

    producer.close()