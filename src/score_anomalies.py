from google.cloud import bigquery

from src.anomaly_model import (
    create_isolation_forest,
    generate_anomaly_predictions,
    generate_anomaly_scores,
    train_isolation_forest,
)
from src.bigquery_client import create_bigquery_client, load_ml_data


RESULTS_TABLE = (
    "open-sky-aviation.aviation_analytics.aircraft_anomaly_results"
)

# Flight behaviour only, so location does not make an aircraft unusual
BEHAVIOR_FEATURES = [
    "velocity",
    "true_track",
    "vertical_rate",
    "geo_altitude",
]

RESULT_COLUMNS = [
    "snapshot_id",
    "icao24",
    "observation_time",
    "velocity",
    "true_track",
    "vertical_rate",
    "geo_altitude",
    "latitude",
    "longitude",
    "behavior_anomaly_score",
    "behavior_anomaly_flag",
]


def score_behavior_anomalies(dataframe):
    """Train the behaviour-only Isolation Forest and score every row."""

    feature_matrix = dataframe[BEHAVIOR_FEATURES]

    model = create_isolation_forest()
    model = train_isolation_forest(model, feature_matrix)

    results = dataframe.copy()

    results["behavior_anomaly_score"] = generate_anomaly_scores(
        model,
        feature_matrix
    )

    # Isolation Forest returns -1 for anomalies; store 1 = anomaly
    results["behavior_anomaly_flag"] = (
        generate_anomaly_predictions(model, feature_matrix) == -1
    ).astype(int)

    return results[RESULT_COLUMNS]


def write_anomaly_results(client, results):
    """Replace the anomaly results table with the new scores."""

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE"
    )

    job = client.load_table_from_dataframe(
        results,
        RESULTS_TABLE,
        job_config=job_config
    )

    job.result()


if __name__ == "__main__":

    client = create_bigquery_client()

    dataframe = load_ml_data(client)

    print("ML rows loaded:", len(dataframe))

    results = score_behavior_anomalies(dataframe)

    write_anomaly_results(client, results)

    print("Rows written:", len(results))
    print(
        "Anomalies flagged:",
        results["behavior_anomaly_flag"].sum()
    )
