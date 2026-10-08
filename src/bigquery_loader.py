import re

from google.cloud import bigquery
from google.cloud import storage


PROJECT_ID = "open-sky-aviation"
DATASET_ID = "aviation_analytics"
TABLE_ID = "raw_snapshot_json"

BUCKET_NAME = "open-sky-aviation-raw"

# Matches raw/aircraft_states_<snapshot_id>.json
SNAPSHOT_FILE_PATTERN = re.compile(
    r"^raw/aircraft_states_([A-Za-z0-9-]+)\.json$"
)


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

    blobs = storage_client.list_blobs(
        BUCKET_NAME,
        prefix="raw/"
    )

    snapshot_ids = []

    for blob in blobs:

        match = SNAPSHOT_FILE_PATTERN.match(
            blob.name
        )

        if match:
            snapshot_ids.append(
                match.group(1)
            )

    return snapshot_ids


def get_existing_snapshot_ids(client):
    """Get snapshot IDs already loaded into raw_snapshot_json."""

    query = f"""
        SELECT DISTINCT snapshot_id
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    """

    results = client.query_and_wait(
        query
    )

    return {
        row.snapshot_id
        for row in results
    }


def build_snapshot_uri(snapshot_id):
    """Build the GCS URI of one snapshot file."""

    return (
        f"gs://{BUCKET_NAME}/raw/"
        f"aircraft_states_{snapshot_id}.json"
    )


def build_load_query(snapshot_ids):
    """Build one LOAD DATA statement for the given snapshots."""

    uris = ",\n            ".join(
        f"'{build_snapshot_uri(snapshot_id)}'"
        for snapshot_id in snapshot_ids
    )

    return f"""
        LOAD DATA INTO `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        FROM FILES (
          format = 'JSON',
          uris = [
            {uris}
          ]
        );
    """


def load_new_snapshots(storage_client, client):
    """Load every GCS snapshot that is not yet in raw_snapshot_json.

    Returns the snapshot IDs that were loaded.
    """

    gcs_snapshot_ids = list_snapshot_ids(
        storage_client
    )

    existing_snapshot_ids = get_existing_snapshot_ids(
        client
    )

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

    if not new_snapshot_ids:
        return []

    # One statement loads all new files together, so a failure
    # leaves the table unchanged rather than half-loaded
    client.query_and_wait(
        build_load_query(new_snapshot_ids)
    )

    for snapshot_id in new_snapshot_ids:
        print(f"Loaded snapshot: {snapshot_id}")

    return new_snapshot_ids


if __name__ == "__main__":

    storage_client = create_storage_client()
    bigquery_client = create_bigquery_client()

    load_new_snapshots(
        storage_client,
        bigquery_client,
    )

    print()
    print("BigQuery RAW loading complete.")
