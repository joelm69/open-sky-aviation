# Global Air Traffic Monitor

An end-to-end data pipeline, anomaly model and Tableau dashboard built on live
aircraft positions from the [OpenSky Network](https://opensky-network.org/).

- **Interactive dashboard:** [Traffic Overview on Tableau Public](https://public.tableau.com/views/aviation_analytics/Traffic_Overview)
- **Case study:** [joeldataportfolio.streamlit.app](https://joeldataportfolio.streamlit.app/open_sky_aviation)

## Overview

OpenSky is a community network of receivers that pick up the position
broadcasts (ADS-B) aircraft send every few seconds. This project collects
snapshots of every aircraft OpenSky can see, stores them in Google Cloud,
transforms them in BigQuery and screens each airborne observation for unusual
flight behaviour with an Isolation Forest model.

The final dataset covers **521,880 observations of 48,577 aircraft across 47
snapshots** between 4 and 8 October 2026.

## Business questions

1. How much air traffic is there, and when does it peak?
2. Where is traffic concentrated?
3. Who is flying: which airlines and registration countries dominate?
4. How are aircraft flying: flight phase, altitude and speed?
5. Which aircraft behave unusually, and why?

## Architecture

```
OpenSky API
    │  Python poller (retries, timeouts, OAuth2 sign-in)
    ▼
Kafka topic "aircraft-states"          ← streaming path: one message per aircraft
    │  consumer regroups messages into complete snapshots
    ▼
Google Cloud Storage (raw JSON, one file per snapshot)
    │  event-driven BigQuery Data Transfer appends each new file
    ▼
BigQuery: raw_snapshot_json → raw → stg → gold → ml
    │  Isolation Forest (scikit-learn)
    ▼
aircraft_anomaly_results
    │
    ▼
Tableau dashboards → Tableau Public → portfolio
```

### BigQuery layers (`open-sky-aviation.aviation_analytics`)

| Table | Contents |
|---|---|
| `raw_snapshot_json` | Landing table: one row per snapshot, aircraft nested in an array |
| `raw_aircraft_states` | One row per aircraft per snapshot, values as sent by OpenSky |
| `stg_aircraft_states` | Unix timestamps converted to `TIMESTAMP` |
| `gold_aircraft_states` | Analysis-ready columns; the source for the dashboards |
| `ml_aircraft_states` | Airborne observations with complete flight data, for the model |
| `aircraft_anomaly_results` | Anomaly score and flag for every scored observation |

## Repository layout

| Path | Purpose |
|---|---|
| `src/opensky_client.py` | Fetches and validates aircraft states from the OpenSky API, with retries and OAuth2 sign-in |
| `src/poll_opensky.py` | Polls OpenSky on an interval and publishes each record to Kafka |
| `src/kafka_producer.py` | Kafka producer for the `aircraft-states` topic |
| `src/kafka_gcs_consumer.py` | Regroups Kafka messages into snapshots and uploads them to Cloud Storage |
| `src/cloud_poll_opensky.py` | Single poll that writes a snapshot straight to Cloud Storage (no Kafka) |
| `src/gcs_client.py` | Reads, validates and writes raw snapshot files in Cloud Storage |
| `src/refresh_warehouse.py` | Rebuilds the raw, stg, gold and ml layers from `raw_snapshot_json` |
| `src/anomaly_model.py` | Isolation Forest helpers |
| `src/bigquery_client.py` | Loads the ML layer from BigQuery |
| `src/score_anomalies.py` | Trains the model and replaces `aircraft_anomaly_results` |
| `src/aviation_anomaly_analysis.ipynb` | Exploratory analysis and model development |
| `tests/` | Unit tests for the client and pollers |
| `Dockerfile` | Container for the single-poll job |

## Running it

Requirements: Python 3.11+, a Google Cloud project with BigQuery and Cloud
Storage, and Google application-default credentials
(`gcloud auth application-default login`). The streaming path also needs a
Kafka broker on `localhost:9092`.

```bash
python -m venv .venv
.venv/bin/pip install requests google-cloud-storage google-cloud-bigquery kafka-python pandas pyarrow db-dtypes scikit-learn pytest
```

Optional: an OpenSky API client raises the request limit. Set its credentials
as environment variables; without them the client uses anonymous access.

```bash
export OPENSKY_CLIENT_ID=...
export OPENSKY_CLIENT_SECRET=...
```

**Collect data** (choose one path):

```bash
# Streaming: poll every 5 minutes into Kafka, and consume into Cloud Storage
.venv/bin/python -m src.poll_opensky
.venv/bin/python -m src.kafka_gcs_consumer

# Batch: one snapshot straight to Cloud Storage
.venv/bin/python -m src.cloud_poll_opensky
```

New files are loaded into `raw_snapshot_json` by the BigQuery Data Transfer.
Don't load them by hand, or they will be appended twice.

**Rebuild the warehouse and rescore anomalies:**

```bash
.venv/bin/python -m src.refresh_warehouse
.venv/bin/python -m src.score_anomalies
```

**Run the tests:**

```bash
.venv/bin/python -m pytest tests
```

One test calls the live OpenSky API.

## Data quality

- Duplicate snapshots in the landing table are removed before they reach the
  raw layer, so no aircraft appears twice in a snapshot in any layer.
- Units are converted to feet and knots for an aviation audience.
- Missing values are labelled openly (`Unknown`, `Not scored`) rather than
  dropped or mislabelled.
- Outliers were inspected before any were excluded: readings above
  50,000 ft are a mix of genuine high-altitude balloons and barometric
  altimeter errors.

## Key findings

- **Traffic builds through the afternoon:** aircraft tracked rose 53% between
  11:20 and 14:40 UTC on 8 October (9,055 → 13,833).
- **Traffic doubles from early morning to mid-afternoon (UTC):** about 6.4K
  aircraft per snapshot at 06:00 against 13.6K at 14:00.
- **Most aircraft are cruising at any moment:** 57.5% of observations are in
  level flight, 32% are climbing or descending and 10% are on the ground.
- **Airliners cruise at 34,000–38,000 ft**, which holds 30% of airborne
  observations.
- **US carriers lead the airline callsigns** (United, American, Delta,
  Southwest), and half of all tracked aircraft are US-registered.
- **The anomaly model flags 5% of scored observations** (23,097 of 461,937).
  Flagged observations climb or descend about 6× more steeply than normal ones,
  at lower altitudes.

## Limitations

- Coverage follows OpenSky's volunteer receivers, so North America and Europe
  are over-represented.
- `origin_country` is the country of registration, not where a flight
  departed; the data contains no airports or routes.
- Snapshots cover selected hours on five days, not continuous 24-hour data.
- Anomalies are a screening signal, not confirmed incidents. The model flags
  the 5% of observations least like the rest by design.

## Engineering notes

The poller first ran on Cloud Run every 15 minutes, but logs showed OpenSky
refusing connections from Google Cloud, so collection moved to a local
machine while storage, loading and modelling stayed in the cloud. Failed polls
now exit with an error instead of reporting success.

## Status

- Traffic Overview dashboard: published
- Fleet & Operations dashboard: built, publishing soon
- Anomaly Screening dashboard: in progress

## Tech stack

Python · Kafka · Google Cloud Storage · BigQuery · SQL · scikit-learn · Tableau · Docker
