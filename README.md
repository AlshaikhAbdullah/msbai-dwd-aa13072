# NYC Weather × Citibike Ridership — Data Pipeline & Dashboard

Coursework for **Dealing with Data Using Python** — NYU Stern MSBAi Program
Course code: XBA1-GB-8217-84 · GCP project: `msbai-dwd-aa13072`

A two-part build: an automated data pipeline that lands Citibike trip data in BigQuery, and a public Streamlit dashboard that lets a non-technical decision-maker explore how NYC weather relates to ridership across the full history (2013–2026).

---

## What this project does

The dashboard answers business questions, not just plots data. Its central question is **"when ridership moves, is it the weather or is it us?"** — separating weather-driven demand swings from operational signals a manager should act on. It also surfaces the commercial angle: casual riders carry higher margins, so the dashboard isolates how their demand responds to weather to inform weather-triggered promotions.

---

## Part 1 — Data Pipeline

Built the pipeline to ingest Citibike trip data and land it as a daily aggregate table in BigQuery, joined to NYC daily weather on `date`.

- **Source data:** Citibike trips, aggregated to daily totals.
- **Weather join:** `nyu-datasets.weather.m_weather_daily_nyc` (temperature, precipitation, snow, wind, calendar fields).
- **Output table:** daily trips with rider-type, geography (NYC / Jersey City), and bike-type breakdowns.
- **Fallback:** `nyu-datasets.citibike.m_daily_trips` when the local pipeline output isn't loaded.

Coverage: 2013-07-01 → 2026-05-29, 4,314 daily rows.

---

## Part 2 — Streamlit Dashboard

A public, interactive dashboard designed for a journalist or city planner — explicitly **not** a data analyst. Built from a written spec (`streamlitspec.md`) and validated against an explicit "done" definition (`VERIFY.md`) before shipping.

### Business questions

| # | Question |
|---|----------|
| Q1 | Is a period's ridership change driven by weather or by something operational we control? |
| Q2 | How does the weather sensitivity of casual riders differ from members? |
| Q3 | Does a weather-triggered promo aimed at higher-margin casual riders make sense? |
| Q4 | What does a typical weather day look like, so an unusual day is recognizable? |
| Q5 | When ridership moves, is it system-wide or localized to one side of the river (NYC vs Jersey City)? |

### Views

- **V1 — Ridership over time, weather overlaid.** Spot whether a dip lines up with bad weather (explainable) or doesn't (worth a manager's attention).
- **V2 — Rides vs temperature, split by rider type.** Where demand is elastic to weather, and for whom.
- **V3 — Member vs casual across weather bands.** Isolates the higher-margin casual segment's weather behavior.
- **V4 — Seasonality.** Rides by month and day-of-week, separating calendar effects from weather effects.
- **V5 — NYC vs Jersey City.** A dip on only one side points to an operational/local cause, not weather.

### Filters

Date range · rider type (member / casual) · weather band (temperature buckets, wet/dry, snow) · geography (NYC / Jersey City) · bike type (classic / electric, 2021 onward).

Weather bands are computed at load: cold (<40°F) / mild (40–60°F) / warm (60–75°F) / hot (>75°F).

---

## Verification

"Done" was defined before building, not assumed after (`VERIFY.md`):

- **Correctness** — `check_correctness.py` reconciles dashboard numbers against the source table. **Result: 28/28 checks pass, 0.0000% deviation** on member+casual and NYC+JC totals.
- **Speed** — full table cached once with `@st.cache_data`; all filtering runs in-memory in pandas, never re-querying BigQuery on interaction.
- **Reach** — deployed to a public URL via Cloud Run with `--allow-unauthenticated`.
- **Clarity** — every chart title states the claim it makes, not a label.

---

## Architecture & Deployment

- **App:** Streamlit (`app.py`), single cached load of the joined daily table.
- **Auth:** plain `bigquery.Client()` — resolves to the developer locally (ADC) and to the attached service account on Cloud Run automatically. No key files in the image.
- **Hosting:** Google Cloud Run, source-based build, scales to zero when idle.
- **Region:** us-central1.

**Live URL:** _<add once public access is confirmed>_

### Run locally

```bash
gcloud auth application-default login
pip install -r requirements.txt
streamlit run app.py
python check_correctness.py   # must print ALL PASS before deploying
```

### Deploy

```bash
gcloud config set project msbai-dwd-aa13072
gcloud run deploy citibike-dashboard --source . \
  --region us-central1 --allow-unauthenticated --platform managed
```

The Cloud Run runtime service account needs `roles/bigquery.jobUser` and `roles/bigquery.dataViewer` on `msbai-dwd-aa13072` (query jobs bill to this project even though the data lives in `nyu-datasets`).

---

## Repository

```
.
├── app.py                 # Streamlit dashboard
├── check_correctness.py   # reconciliation check vs source table
├── requirements.txt       # pinned dependencies
├── Dockerfile             # binds $PORT / 0.0.0.0 for Cloud Run
├── streamlitspec.md       # product spec
└── VERIFY.md              # "done" targets
```

---

*Built with Claude Code.*
