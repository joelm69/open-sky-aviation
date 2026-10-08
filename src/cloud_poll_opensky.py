from src.gcs_client import write_raw_snapshot
from src.opensky_client import fetch_aircraft_states


def poll_once():
    print("Starting OpenSky polling...")

    records = fetch_aircraft_states()

    print(f"Collected {len(records)} aircraft records")

    if not records:
        # Exit non-zero so Cloud Run marks the execution as failed
        # instead of reporting an empty run as a success
        raise SystemExit("No records collected.")

    write_raw_snapshot(records)

    print("Polling cycle completed.")


if __name__ == "__main__":
    poll_once()