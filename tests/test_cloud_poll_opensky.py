from unittest.mock import patch

import pytest

from src.cloud_poll_opensky import poll_once


def test_poll_once_fails_when_no_records_collected():
    with patch(
        "src.cloud_poll_opensky.fetch_aircraft_states",
        return_value=[]
    ), patch(
        "src.cloud_poll_opensky.write_raw_snapshot"
    ) as mock_write:

        with pytest.raises(SystemExit) as error:
            poll_once()

    assert error.value.code != 0
    mock_write.assert_not_called()


def test_poll_once_writes_collected_records():
    fake_records = [
        {"icao24": "abc123"},
    ]

    with patch(
        "src.cloud_poll_opensky.fetch_aircraft_states",
        return_value=fake_records
    ), patch(
        "src.cloud_poll_opensky.write_raw_snapshot"
    ) as mock_write:
        poll_once()

    mock_write.assert_called_once_with(fake_records)
