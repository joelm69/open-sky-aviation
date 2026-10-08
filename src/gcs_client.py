import json

from google.cloud import storage


def read_raw_snapshot(snapshot_id):
    client = storage.Client(project="open-sky-aviation")

    bucket = client.bucket("open-sky-aviation-raw")

    blob = bucket.blob(
        f"raw/aircraft_states_{snapshot_id}.json"
    )

    raw_data = blob.download_as_text()

    return json.loads(raw_data)


def validate_snapshot(data):
    if not isinstance(data, dict):
        raise ValueError("Snapshot is not a dictionary")

    required_top_level_fields = [
        "snapshot_id",
        "collected_at",
        "aircraft",
    ]

    for field in required_top_level_fields:
        if field not in data:
            raise ValueError(
                f"Missing top-level field: {field}"
            )

    if not isinstance(data["aircraft"], list):
        raise ValueError("Aircraft field is not a list")

    print("Top-level structure: valid")
    print("Aircraft records:", len(data["aircraft"]))

    if not data["aircraft"]:
        raise ValueError("Aircraft list is empty")

    required_aircraft_fields = [
        "icao24",
        "callsign",
        "origin_country",
        "longitude",
        "latitude",
        "baro_altitude",
        "on_ground",
        "velocity",
        "true_track",
        "vertical_rate",
        "geo_altitude",
        "snapshot_id",
        "collected_at",
    ]

    first_aircraft = data["aircraft"][0]

    for field in required_aircraft_fields:
        if field not in first_aircraft:
            raise ValueError(
                f"Missing aircraft field: {field}"
            )

    print("Aircraft structure: valid")
    print("Required fields:", len(required_aircraft_fields))

    snapshot_id = data["snapshot_id"]

    inconsistent_ids = sum(
        aircraft.get("snapshot_id") != snapshot_id
        for aircraft in data["aircraft"]
    )

    print("Inconsistent snapshot IDs:", inconsistent_ids)

    if inconsistent_ids > 0:
        raise ValueError(
            "Some aircraft records have a different snapshot ID"
        )

    print("Snapshot validation: passed")
    
def write_raw_snapshot(records):
    client = storage.Client(project="open-sky-aviation")

    bucket = client.bucket("open-sky-aviation-raw")

    snapshot_id = records[0]["snapshot_id"]

    data = {
        "snapshot_id": snapshot_id,
        "collected_at": records[0]["collected_at"],
        "aircraft": records,
    }

    blob = bucket.blob(
        f"raw/aircraft_states_{snapshot_id}.json"
    )

    blob.upload_from_string(
        json.dumps(
            data,
            default=lambda obj: obj.isoformat()
        ),
        content_type="application/json",
    )

    print("Snapshot written to GCS:", snapshot_id)
    print("Aircraft records:", len(records))

if __name__ == "__main__":
    snapshot_id = (
        "39d9aeae-6d1a-4e39-a807-3709bd5facf6"
    )

    data = read_raw_snapshot(snapshot_id)

    validate_snapshot(data)