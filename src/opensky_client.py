import os
import time
import uuid
from datetime import datetime, timezone

import requests


TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)

# Refresh the token this many seconds before OpenSky says it expires
TOKEN_EXPIRY_MARGIN = 60

_token_cache = {
    "access_token": None,
    "expires_at": 0,
}


def get_access_token():
    """Get an OpenSky OAuth2 token, or None to use anonymous access.

    Reads OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET from the
    environment and reuses the token until it is close to expiring.
    """

    client_id = os.environ.get("OPENSKY_CLIENT_ID")
    client_secret = os.environ.get("OPENSKY_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    if (
        _token_cache["access_token"]
        and time.time() < _token_cache["expires_at"]
    ):
        return _token_cache["access_token"]

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30
    )

    response.raise_for_status()

    token_data = response.json()

    _token_cache["access_token"] = token_data["access_token"]
    _token_cache["expires_at"] = (
        time.time()
        + token_data.get("expires_in", 1800)
        - TOKEN_EXPIRY_MARGIN
    )

    print("OpenSky access token obtained")

    return _token_cache["access_token"]


def build_auth_headers():
    """Build request headers, with a bearer token when credentials exist."""

    token = get_access_token()

    if token is None:
        print("No OpenSky credentials found, using anonymous access")
        return {}

    return {"Authorization": f"Bearer {token}"}


def wait_before_retry(attempt, max_retries):
    """Wait using exponential backoff if retries remain."""

    if attempt >= max_retries:
        print("Maximum retries reached.")
        return False

    wait_time = 2 ** attempt
    print(f"Waiting {wait_time} seconds before retry...")
    time.sleep(wait_time)

    return True

def fetch_aircraft_states(
    url="https://opensky-network.org/api/states/all",
    params=None,
    max_retries=3,
    timeout=30
):

    try:
        headers = build_auth_headers()

        for attempt in range(max_retries + 1):

            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout
                )

            except requests.exceptions.Timeout:
                print("Request timed out.")

                if wait_before_retry(attempt, max_retries):
                    continue

                return []

            except requests.exceptions.ConnectionError:
                print("Connection error.")

                if wait_before_retry(attempt, max_retries):
                    continue

                return []

            if response.status_code == 401 and headers:
                print("OpenSky token rejected, requesting a new one.")

                _token_cache["access_token"] = None
                headers = build_auth_headers()

                if wait_before_retry(attempt, max_retries):
                    continue

                return []

            if response.status_code == 429:
                print("Rate limit reached.")

                if wait_before_retry(attempt, max_retries):
                    continue

                return []

            if response.status_code >= 500:
                print("OpenSky server error:", response.status_code)

                if wait_before_retry(attempt, max_retries):
                    continue

                return []

            response.raise_for_status()
            break

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError("Unexpected response format")

        if "states" not in data:
            raise ValueError("Missing states field")

        if not isinstance(data["states"], list):
            raise ValueError("States field is not a list")

        field_names = [
            "icao24",
            "callsign",
            "origin_country",
            "time_position",
            "last_contact",
            "longitude",
            "latitude",
            "baro_altitude",
            "on_ground",
            "velocity",
            "true_track",
            "vertical_rate",
            "sensors",
            "geo_altitude",
            "squawk",
            "spi",
            "position_source",
        ]

        snapshot_id = str(uuid.uuid4())
        collected_at = datetime.now(timezone.utc)
        aircraft_records = []

        for state in data["states"]:
            if not isinstance(state, list):
                raise ValueError("Aircraft state is not a list")

            if len(state) != len(field_names):
                raise ValueError(
                    "Unexpected number of fields in aircraft state"
                )

            aircraft = dict(zip(field_names, state))
            aircraft["snapshot_id"] = snapshot_id
            aircraft["collected_at"] = collected_at
            aircraft_records.append(aircraft)

        print("Response validated")
        print("Number of aircraft:", len(data["states"]))

        if data["states"]:
            print(
                "Fields in first aircraft record:",
                len(data["states"][0])
            )
        else:
            print("Fields in first aircraft record: 0")

        return aircraft_records

    except requests.exceptions.RequestException as error:
        print("Request failed:", error)
        return []

    except ValueError as error:
        print("Invalid response:", error)
        return []

if __name__ == "__main__":
    aircraft_records = fetch_aircraft_states()

    if aircraft_records:
        print("Structured aircraft records:", len(aircraft_records))
        print(aircraft_records[0])
    else:
        print("No aircraft records found")    