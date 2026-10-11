# Global Air Traffic Monitor

**How busy is the sky, who is flying in it, and which flights look unusual?**

An end-to-end data project: live aircraft positions collected from the
OpenSky Network, cleaned in Google BigQuery, screened with machine learning
and presented in three interactive Tableau dashboards.

**[Explore the dashboards →](https://public.tableau.com/views/aviation_analytics/Traffic_Overview)**
&nbsp;·&nbsp;
**[Read the case study →](https://joeldataportfolio.streamlit.app/open_sky_aviation)**

**521,880** observations · **48,577** aircraft · **4–8 October 2026**

---

## Key findings

- **Traffic doubles through the day:** from about 6,400 aircraft in the early morning to 13,600 by mid-afternoon (UTC).
- **US airlines dominate:** United, American, Delta and Southwest lead, and half of all aircraft are US-registered.
- **6 in 10 aircraft are cruising at any moment**, mostly at 34,000–38,000 ft.
- **The ML model flags 5% of observations as unusual:** flights climbing or descending about 6× more steeply than normal. It also caught a research balloon and faulty sensor readings.

## Dashboards

| | |
|---|---|
| **[Traffic Overview](https://public.tableau.com/views/aviation_analytics/Traffic_Overview)** | How much traffic, when it peaks and where |
| **[Fleet & Operations](https://public.tableau.com/views/aviation_analytics/Fleet_Operations)** | Top airlines and countries; click an airline to compare it |
| **[Anomaly Screening](https://public.tableau.com/views/aviation_analytics/Anomaly_Screening)** | Which flights look unusual and why |

## Skills demonstrated

**Data engineering** (Python, Kafka, Google Cloud) · **SQL and data modelling** (BigQuery) · **Data quality** · **Machine learning** (Isolation Forest) · **Data visualisation** (Tableau) · **Problem solving:** when OpenSky blocked requests from Google Cloud, I diagnosed it from the logs and moved data collection off the cloud while keeping storage and analysis in it.

---

<details>
<summary><strong>Technical details: how it works and how to run it</strong></summary>

### Pipeline

```
OpenSky API → Python poller → Kafka → Google Cloud Storage
  → BigQuery Data Transfer → BigQuery (raw → stg → gold → ml)
  → Isolation Forest (scikit-learn) → Tableau
```

### BigQuery tables (`open-sky-aviation.aviation_analytics`)

| Table | Contents |
|---|---|
| `raw_snapshot_json` | Landing table: one row per snapshot |
| `raw_aircraft_states` | One row per aircraft per snapshot |
| `stg_aircraft_states` | Timestamps converted |
| `gold_aircraft_states` | Analysis-ready data used by the dashboards |
| `ml_aircraft_states` | Airborne observations with complete data, for the model |
| `aircraft_anomaly_results` | Anomaly score and flag for each scored observation |

### Code

| Path | Purpose |
|---|---|
| `src/opensky_client.py` | Fetches aircraft positions, with retries and OAuth2 sign-in |
| `src/poll_opensky.py`, `src/kafka_producer.py` | Poll OpenSky and publish each record to Kafka |
| `src/kafka_gcs_consumer.py` | Regroup Kafka messages into snapshots and upload them to Cloud Storage |
| `src/cloud_poll_opensky.py` | Single poll straight to Cloud Storage |
| `src/refresh_warehouse.py` | Rebuild the BigQuery layers from the landing table |
| `src/score_anomalies.py`, `src/anomaly_model.py` | Train the model and score every observation |
| `src/aviation_anomaly_analysis.ipynb` | Exploratory analysis |
| `tests/` | Unit tests |

### Run it

Requires Python 3.11+, a Google Cloud project with BigQuery and Cloud Storage,
and application-default credentials. The streaming path also needs Kafka on
`localhost:9092`.

```bash
python -m venv .venv
.venv/bin/pip install requests google-cloud-storage google-cloud-bigquery kafka-python pandas pyarrow db-dtypes scikit-learn pytest

# Collect data: streaming via Kafka...
.venv/bin/python -m src.poll_opensky
.venv/bin/python -m src.kafka_gcs_consumer
# ...or one snapshot straight to Cloud Storage
.venv/bin/python -m src.cloud_poll_opensky

# Rebuild the warehouse and rescore anomalies
.venv/bin/python -m src.refresh_warehouse
.venv/bin/python -m src.score_anomalies

# Tests (one calls the live OpenSky API)
.venv/bin/python -m pytest tests
```


</details>
