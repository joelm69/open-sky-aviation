from google.cloud import bigquery


PROJECT_ID = "open-sky-aviation"
DATASET = f"{PROJECT_ID}.aviation_analytics"

# Snapshots written while testing the poller, not real collections
TEST_SNAPSHOT_IDS = [
    "poll-test-001",
]


# Each step rebuilds one layer from the layer before it:
# raw_snapshot_json -> raw -> stg -> gold -> ml
REFRESH_STEPS = [
    (
        "raw_aircraft_states",
        f"""
        TRUNCATE TABLE `{DATASET}.raw_aircraft_states`;

        INSERT INTO `{DATASET}.raw_aircraft_states`
        (
            snapshot_id,
            collected_at,
            icao24,
            callsign,
            origin_country,
            time_position,
            last_contact,
            longitude,
            latitude,
            baro_altitude,
            on_ground,
            velocity,
            true_track,
            vertical_rate,
            sensors,
            geo_altitude,
            squawk,
            spi,
            position_source
        )
        SELECT
            snapshot.snapshot_id,
            snapshot.collected_at,
            aircraft.icao24,
            aircraft.callsign,
            aircraft.origin_country,
            aircraft.time_position,
            aircraft.last_contact,
            aircraft.longitude,
            aircraft.latitude,
            aircraft.baro_altitude,
            aircraft.on_ground,
            aircraft.velocity,
            aircraft.true_track,
            aircraft.vertical_rate,
            PARSE_JSON(aircraft.sensors),
            aircraft.geo_altitude,
            CAST(aircraft.squawk AS STRING),
            aircraft.spi,
            aircraft.position_source
        FROM
            (
                -- A snapshot file can be appended more than once
                -- (e.g. by the GCS transfer and a manual load),
                -- so keep one copy of each snapshot
                SELECT * EXCEPT(row_num)
                FROM (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY snapshot_id
                            ORDER BY collected_at
                        ) AS row_num
                    FROM
                        `{DATASET}.raw_snapshot_json`
                )
                WHERE
                    row_num = 1
            ) AS snapshot,
            UNNEST(snapshot.aircraft) AS aircraft
        WHERE
            snapshot.snapshot_id NOT IN UNNEST(@test_snapshot_ids);
        """,
    ),
    (
        "stg_aircraft_states",
        f"""
        TRUNCATE TABLE `{DATASET}.stg_aircraft_states`;

        INSERT INTO `{DATASET}.stg_aircraft_states`
        (
            snapshot_id,
            collected_at,
            icao24,
            callsign,
            origin_country,
            time_position,
            last_contact,
            longitude,
            latitude,
            baro_altitude,
            on_ground,
            velocity,
            true_track,
            vertical_rate,
            sensors,
            geo_altitude,
            squawk,
            spi,
            position_source
        )
        SELECT
            snapshot_id,
            collected_at,
            icao24,
            callsign,
            origin_country,
            TIMESTAMP_SECONDS(time_position) AS time_position,
            TIMESTAMP_SECONDS(last_contact) AS last_contact,
            longitude,
            latitude,
            baro_altitude,
            on_ground,
            velocity,
            true_track,
            vertical_rate,
            sensors,
            geo_altitude,
            squawk,
            spi,
            position_source
        FROM
            `{DATASET}.raw_aircraft_states`;
        """,
    ),
    (
        "gold_aircraft_states",
        f"""
        TRUNCATE TABLE `{DATASET}.gold_aircraft_states`;

        INSERT INTO `{DATASET}.gold_aircraft_states`
        (
            snapshot_id,
            collected_at,
            icao24,
            callsign,
            origin_country,
            observation_time,
            last_contact,
            longitude,
            latitude,
            baro_altitude,
            geo_altitude,
            velocity,
            true_track,
            vertical_rate,
            on_ground,
            squawk,
            spi,
            position_source
        )
        SELECT
            snapshot_id,
            collected_at,
            icao24,
            callsign,
            origin_country,
            time_position AS observation_time,
            last_contact,
            longitude,
            latitude,
            baro_altitude,
            geo_altitude,
            velocity,
            true_track,
            vertical_rate,
            on_ground,
            squawk,
            spi,
            position_source
        FROM
            `{DATASET}.stg_aircraft_states`;
        """,
    ),
    (
        "ml_aircraft_states",
        f"""
        TRUNCATE TABLE `{DATASET}.ml_aircraft_states`;

        INSERT INTO `{DATASET}.ml_aircraft_states`
        (
            snapshot_id,
            collected_at,
            icao24,
            observation_time,
            velocity,
            true_track,
            vertical_rate,
            geo_altitude,
            latitude,
            longitude
        )
        SELECT
            snapshot_id,
            collected_at,
            icao24,
            observation_time,
            velocity,
            true_track,
            vertical_rate,
            geo_altitude,
            latitude,
            longitude
        FROM
            `{DATASET}.gold_aircraft_states`
        WHERE
            on_ground = FALSE
            AND velocity IS NOT NULL
            AND true_track IS NOT NULL
            AND vertical_rate IS NOT NULL
            AND geo_altitude IS NOT NULL
            AND latitude IS NOT NULL
            AND longitude IS NOT NULL;
        """,
    ),
]


def count_table(client, table_name):
    """Count rows and snapshots in one warehouse table."""

    query = f"""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT snapshot_id) AS snapshots
        FROM
            `{DATASET}.{table_name}`
    """

    row = list(client.query_and_wait(query))[0]

    return row.row_count, row.snapshots


def refresh_warehouse(client):
    """Rebuild every layer from raw_snapshot_json, in order."""

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "test_snapshot_ids",
                "STRING",
                TEST_SNAPSHOT_IDS,
            ),
        ]
    )

    for table_name, query in REFRESH_STEPS:

        print(f"Rebuilding {table_name}...")

        client.query_and_wait(
            query,
            job_config=job_config,
        )

        row_count, snapshots = count_table(
            client,
            table_name,
        )

        print(
            f"{table_name}: {row_count} rows, "
            f"{snapshots} snapshots"
        )


if __name__ == "__main__":

    client = bigquery.Client(
        project=PROJECT_ID
    )

    refresh_warehouse(client)

    print()
    print("Warehouse refresh complete.")
