from google.cloud import bigquery


PROJECT_ID = "open-sky-aviation"


def create_bigquery_client():
    """Create a BigQuery client using local Google authentication."""

    client = bigquery.Client(project=PROJECT_ID)

    return client

def load_ml_data(client):
    """Load the ML-ready aircraft observations from BigQuery."""
    query = """
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
            `open-sky-aviation.aviation_analytics.ml_aircraft_states`
    """
    dataframe = client.query(query).to_dataframe()
    return dataframe

def prepare_ml_features(dataframe):
    """Select the features used by the Isolation Forest model."""

    features = [
        "velocity",
        "true_track",
        "vertical_rate",
        "geo_altitude",
        "latitude",
        "longitude",
    ]

    feature_matrix = dataframe[features]

    return feature_matrix