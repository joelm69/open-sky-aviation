from unittest.mock import MagicMock

from src.bigquery_loader import (
    build_load_query,
    list_snapshot_ids,
    load_new_snapshots,
)


def make_blob(name):
    blob = MagicMock()
    blob.name = name
    return blob


def test_list_snapshot_ids_keeps_only_snapshot_files():
    storage_client = MagicMock()
    storage_client.list_blobs.return_value = [
        make_blob("raw/aircraft_states_abc-123.json"),
        make_blob("raw/aircraft_states_def-456.json"),
        make_blob("raw/notes.txt"),
        make_blob("raw/aircraft_states_bad.csv"),
    ]

    assert list_snapshot_ids(storage_client) == [
        "abc-123",
        "def-456",
    ]


def test_build_load_query_lists_every_uri():
    query = build_load_query(["abc-123", "def-456"])

    assert "LOAD DATA INTO" in query
    assert (
        "gs://open-sky-aviation-raw/raw/aircraft_states_abc-123.json"
        in query
    )
    assert (
        "gs://open-sky-aviation-raw/raw/aircraft_states_def-456.json"
        in query
    )


def test_load_new_snapshots_skips_already_loaded():
    storage_client = MagicMock()
    storage_client.list_blobs.return_value = [
        make_blob("raw/aircraft_states_old.json"),
        make_blob("raw/aircraft_states_new.json"),
    ]

    client = MagicMock()
    old_row = MagicMock()
    old_row.snapshot_id = "old"
    client.query_and_wait.side_effect = [
        [old_row],
        None,
    ]

    loaded = load_new_snapshots(storage_client, client)

    assert loaded == ["new"]

    load_query = client.query_and_wait.call_args_list[1].args[0]
    assert "aircraft_states_new.json" in load_query
    assert "aircraft_states_old.json" not in load_query


def test_load_new_snapshots_does_nothing_when_up_to_date():
    storage_client = MagicMock()
    storage_client.list_blobs.return_value = [
        make_blob("raw/aircraft_states_old.json"),
    ]

    client = MagicMock()
    old_row = MagicMock()
    old_row.snapshot_id = "old"
    client.query_and_wait.return_value = [old_row]

    loaded = load_new_snapshots(storage_client, client)

    assert loaded == []
    assert client.query_and_wait.call_count == 1
