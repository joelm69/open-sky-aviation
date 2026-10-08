from unittest.mock import patch

import requests

from src import opensky_client
from src.opensky_client import fetch_aircraft_states


def test_fetch_aircraft_states_success():
    records = fetch_aircraft_states()

    assert isinstance(records, list)
    assert len(records) > 0


def test_fetch_aircraft_states_retries_after_rate_limit():
    mock_responses = [
        type("Response", (), {
            "status_code": 429,
            "raise_for_status": lambda self: None,
        })(),
        type("Response", (), {
            "status_code": 429,
            "raise_for_status": lambda self: None,
        })(),
        type("Response", (), {
            "status_code": 200,
            "raise_for_status": lambda self: None,
            "json": lambda self: {
                "time": 1234567890,
                "states": []
            },
        })(),
    ]

    with patch(
        "src.opensky_client.requests.get",
        side_effect=mock_responses
    ):
        records = fetch_aircraft_states()

    assert records == []


def test_fetch_aircraft_states_rejects_malformed_state():
    malformed_response = type("Response", (), {
        "status_code": 200,
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "time": 1234567890,
            "states": [
                [
                    "39de4e",
                    "TVF8602",
                    "France"
                ]
            ]
        },
    })()

    with patch(
        "src.opensky_client.requests.get",
        return_value=malformed_response
    ):
        records = fetch_aircraft_states()

    assert records == []


def test_fetch_aircraft_states_retries_after_timeout():
    with patch(
        "src.opensky_client.requests.get",
        side_effect=[
            requests.exceptions.Timeout(),
            type("Response", (), {
                "status_code": 200,
                "raise_for_status": lambda self: None,
                "json": lambda self: {
                    "time": 1234567890,
                    "states": []
                },
            })(),
        ]
    ):
        records = fetch_aircraft_states()

    assert records == []


def test_fetch_aircraft_states_retries_after_server_error():
    with patch(
        "src.opensky_client.requests.get",
        side_effect=[
            type("Response", (), {
                "status_code": 500,
                "raise_for_status": lambda self: None,
            })(),
            type("Response", (), {
                "status_code": 200,
                "raise_for_status": lambda self: None,
                "json": lambda self: {
                    "time": 1234567890,
                    "states": []
                },
            })(),
        ]
    ):
        records = fetch_aircraft_states()

    assert records == []

def test_fetch_aircraft_states_sends_bearer_token(monkeypatch):
    monkeypatch.setenv("OPENSKY_CLIENT_ID", "test-client")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "test-secret")
    monkeypatch.setitem(
        opensky_client._token_cache, "access_token", None
    )

    token_response = type("Response", (), {
        "status_code": 200,
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "access_token": "abc123",
            "expires_in": 1800,
        },
    })()

    states_response = type("Response", (), {
        "status_code": 200,
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "time": 1234567890,
            "states": []
        },
    })()

    with patch(
        "src.opensky_client.requests.post",
        return_value=token_response
    ) as mock_post, patch(
        "src.opensky_client.requests.get",
        return_value=states_response
    ) as mock_get:
        records = fetch_aircraft_states()

    assert records == []
    mock_post.assert_called_once()
    assert mock_get.call_args.kwargs["headers"] == {
        "Authorization": "Bearer abc123"
    }


def test_fetch_aircraft_states_is_anonymous_without_credentials(
    monkeypatch
):
    monkeypatch.delenv("OPENSKY_CLIENT_ID", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_SECRET", raising=False)

    states_response = type("Response", (), {
        "status_code": 200,
        "raise_for_status": lambda self: None,
        "json": lambda self: {
            "time": 1234567890,
            "states": []
        },
    })()

    with patch(
        "src.opensky_client.requests.post"
    ) as mock_post, patch(
        "src.opensky_client.requests.get",
        return_value=states_response
    ) as mock_get:
        fetch_aircraft_states()

    mock_post.assert_not_called()
    assert mock_get.call_args.kwargs["headers"] == {}
