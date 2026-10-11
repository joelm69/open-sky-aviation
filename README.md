# Global Air Traffic Monitor

**How busy is the sky, who is flying in it, and which flights look unusual?**

I built a system that collects live aircraft positions from around the world,
cleans and organises the data in the cloud, uses machine learning to spot
unusual flights, and presents the results in interactive Tableau dashboards.

**[View the interactive dashboard →](https://public.tableau.com/views/aviation_analytics/Traffic_Overview)**
&nbsp;·&nbsp;
**[Read the full case study →](https://joeldataportfolio.streamlit.app/open_sky_aviation)**

---

## At a glance

| | |
|---|---|
| **Data analysed** | 521,880 aircraft observations |
| **Aircraft tracked** | 48,577 |
| **Period** | 4–8 October 2026 |
| **Source** | OpenSky Network, a public feed of live aircraft positions |
| **Tools** | Python · SQL · Google Cloud · BigQuery · Kafka · Machine learning · Tableau |

## The questions I set out to answer

1. How much air traffic is there, and when is it busiest?
2. Where in the world is traffic concentrated?
3. Which airlines and countries have the most aircraft in the sky?
4. How do aircraft spend their time: cruising, climbing, descending or on the ground?
5. Which flights behave unusually, and why?

## What I found

- **Traffic grows quickly through the day.** The number of aircraft in the
  sky rose **53% in three hours** on 8 October, and it **more than doubles**
  from early morning to mid-afternoon (UTC).
- **US airlines dominate.** United, American, Delta and Southwest have the
  most aircraft tracked, and **half of all aircraft are registered in the US**.
- **Most aircraft are cruising at any moment.** About 6 in 10 are in level
  flight, 3 in 10 are climbing or descending near airports, and 1 in 10 is on
  the ground.
- **Airliners cruise at 34,000–38,000 ft**, the altitude band holding 30% of
  airborne traffic.
- **Different airlines have different "signatures".** Regional airlines spend
  more time on the ground and less time at cruising height than major
  airlines, because their flights are shorter.
- **The machine-learning model flags about 5% of observations as unusual.**
  These are mostly aircraft climbing or descending far more steeply than
  normal. It also caught a high-altitude research balloon and several faulty
  sensor readings.

## Recommendations

- **Plan staffing around the afternoon peak**, when traffic is highest, and
  schedule maintenance in the quieter early-morning hours.
- **Use the anomaly model as a review queue, not an alarm.** Start with the
  aircraft flagged most often.
- **Build automatic data-quality checks into the pipeline**, such as
  comparing an aircraft's two altitude readings, so faulty data is caught
  early.
- **Widen data coverage before drawing global conclusions**, especially for
  Africa and Asia.

## The dashboards

| Dashboard | What it shows | Status |
|---|---|---|
| **Traffic Overview** | Headline numbers, a live map of aircraft, and how traffic changes through the day | [Published](https://public.tableau.com/views/aviation_analytics/Traffic_Overview) |
| **Fleet & Operations** | Top airlines and countries, flight phases and cruising altitudes. Click an airline to compare it with the rest | Built, publishing soon |
| **Anomaly Screening** | The flights the model flagged, where they are and what makes them unusual | In progress |

## Skills this project demonstrates

- **Data engineering:** collecting live data automatically, streaming it with
  Kafka and storing it in Google Cloud.
- **SQL and data modelling:** turning raw data into clean, analysis-ready
  tables in BigQuery.
- **Data quality:** removing duplicates, checking outliers before deleting
  them, and labelling missing data honestly.
- **Machine learning:** an Isolation Forest model that screens for unusual
  flight behaviour.
- **Data visualisation:** interactive Tableau dashboards designed around
  business questions.
- **Problem solving:** when the data provider blocked requests from Google
  Cloud, I diagnosed it from the logs and redesigned the collection step while
  keeping the rest of the system in the cloud.

## Being honest about the data

- OpenSky relies on volunteer receivers, so North America and Europe are
  covered best. The numbers reflect the aircraft OpenSky could see, not every
  flight in the world.
- An aircraft's "country" is where it is registered, not where it flew from.
- The data covers selected hours over five days, not every hour.
- Flagged flights are worth a second look, not confirmed incidents.

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

Set `OPENSKY_CLIENT_ID` and `OPENSKY_CLIENT_SECRET` to use an OpenSky API
client; without them the poller uses anonymous access. New files in Cloud
Storage are loaded into BigQuery by an event-driven Data Transfer, so don't
load them by hand.

</details>
