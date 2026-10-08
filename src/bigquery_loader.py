import json

from google.cloud import bigquery
from google.cloud import storage


PROJECT_ID = "open-sky-aviation"
DATASET_ID = "aviation_analytics"
TABLE_ID = "raw_aircraft_states"

BUCKET_NAME = "open-sky-aviation-raw"


def create_bigquery_client():
    """Create a BigQuery client."""

    return bigquery.Client(
        project=PROJECT_ID
    )


def create_storage_client():
    """Create a Google Cloud Storage client."""

    return storage.Client(
        project=PROJECT_ID
    )


def list_snapshot_ids(storage_client):
    """Find all aircraft snapshot IDs stored in GCS."""

    bucket = storage_client.bucket(
        BUCKET_NAME
    )

    blobs = bucket.list_blobs(
        prefix="raw/"
    )

    snapshot_ids = []

    for blob in blobs:

        filename = blob.name.split("/")[-1]

        if not filename.startswith(
            "aircraft_states_"
        ):
            continue

        if not filename.endswith(".json"):
            continue

        snapshot_id = filename[
            len("aircraft_states_"):-len(".json")
        ]

        snapshot_ids.append(
            snapshot_id
        )

    return snapshot_ids


def get_existing_snapshot_ids(client):
    """Get snapshot IDs already loaded into BigQuery."""

    query = f"""
        SELECT DISTINCT snapshot_id
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    """

    results = client.query(
        query
    ).result()

    return {
        row.snapshot_id
        for row in results
    }


def read_raw_snapshot(storage_client, snapshot_id):
    """Read one raw snapshot from GCS."""

    bucket = storage_client.bucket(
        BUCKET_NAME
    )

    blob = bucket.blob(
        f"raw/aircraft_states_{snapshot_id}.json"
    )

    raw_data = blob.download_as_text()

    return json.loads(
        raw_data
    )


def prepare_aircraft_rows(snapshot):
    """Convert one snapshot into BigQuery-compatible rows."""

    rows = []

    for aircraft in snapshot["aircraft"]:

        row = {
            "snapshot_id": aircraft["snapshot_id"],
            "collected_at": aircraft["collected_at"],

            "icao24": aircraft["icao24"],
            "callsign": aircraft["callsign"],
            "origin_country": aircraft["origin_country"],

            "time_position": aircraft["time_position"],
            "last_contact": aircraft["last_contact"],

            "longitude": aircraft["longitude"],
            "latitude": aircraft["latitude"],
            "baro_altitude": aircraft["baro_altitude"],

            "on_ground": aircraft["on_ground"],

            "velocity": aircraft["velocity"],
            "true_track": aircraft["true_track"],
            "vertical_rate": aircraft["vertical_rate"],

            "sensors": aircraft["sensors"],

            "geo_altitude": aircraft["geo_altitude"],
            "squawk": aircraft["squawk"],
            "spi": aircraft["spi"],
            "position_source": aircraft["position_source"],
        }

        rows.append(
            row
        )

    return rows


def insert_aircraft_rows(client, rows):
    """Insert aircraft rows into BigQuery RAW."""

    table_reference = (
        f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    )

    errors = client.insert_rows_json(
        table_reference,
        rows,
    )

    if errors:
        raise RuntimeError(
            f"BigQuery insert failed: {errors}"
        )

    print(
        f"Inserted {len(rows)} aircraft rows into BigQuery"
    )


if __name__ == "__main__":

    storage_client = create_storage_client()
    bigquery_client = create_bigquery_client()

    # Find snapshots available in GCS
    gcs_snapshot_ids = list_snapshot_ids(
        storage_client
    )

    # Find snapshots already loaded into BigQuery
    existing_snapshot_ids = get_existing_snapshot_ids(
        bigquery_client
    )

    # Only process snapshots that have not been loaded yet
    new_snapshot_ids = [
        snapshot_id
        for snapshot_id in gcs_snapshot_ids
        if snapshot_id not in existing_snapshot_ids
    ]

    print(
        f"GCS snapshots found: {len(gcs_snapshot_ids)}"
    )

    print(
        f"Snapshots already in BigQuery: "
        f"{len(existing_snapshot_ids)}"
    )

    print(
        f"New snapshots to load: "
        f"{len(new_snapshot_ids)}"
    )

    # Load each new snapshot
    for snapshot_id in new_snapshot_ids:

        print()
        print(
            f"Loading snapshot: {snapshot_id}"
        )

        snapshot = read_raw_snapshot(
            storage_client,
            snapshot_id,
        )

        rows = prepare_aircraft_rows(
            snapshot
        )

        print(
            f"Prepared {len(rows)} aircraft rows"
        )

        insert_aircraft_rows(
            bigquery_client,
            rows,
        )

    print()
    print(
        "BigQuery RAW loading complete."
    )