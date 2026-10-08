from unittest.mock import patch

from src.poll_opensky import poll_and_publish


def test_poll_and_publish_runs_expected_number_of_cycles():
    fake_records = [
        {"icao24": "abc123"},
        {"icao24": "def456"},
    ]

    with patch(
        "src.poll_opensky.fetch_aircraft_states",
        return_value=fake_records
    ) as mock_fetch, patch(
        "src.poll_opensky.create_producer"
    ) as mock_create_producer, patch(
        "src.poll_opensky.send_aircraft_records"
    ) as mock_send:

        producer = mock_create_producer.return_value

        poll_and_publish(
            interval_seconds=0,
            cycles=3
        )

    assert mock_fetch.call_count == 3
    assert mock_send.call_count == 3
    assert mock_send.call_args_list[0].args == (
        producer,
        fake_records,
    )
    producer.close.assert_called_once()