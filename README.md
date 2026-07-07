# NYC Weather × Citibike Ridership — Data Pipeline & Dashboard

Coursework for **Dealing with Data Using Python** — NYU Stern MSBAi Program.
GCP project: `msbai-dwd-aa13072`

A two-part build: an automated data pipeline that lands the full Citibike trip
history in BigQuery, and a public Streamlit dashboard that lets a non-technical
decision-maker explore how NYC weather relates to ridership (2013–present, NYC +
Jersey City).

## Live dashboard

**Public URL:** <https://msbai-dwd-aa13072-kezv8xk9u8iclxichuno3q.streamlit.app/>

Opens with no login; loads in ~10 s (data cached once, all filtering in-memory).

---

## What this project does

The dashboard answers business questions, not just plots data. Its central
question is **"when ridership moves, is it the weather or is it us?"** —
separating weather-driven demand swings from operational signals a manager
should act on. It also surfaces the commercial angle: casual riders carry higher
margins, so it isolates how their demand responds to weather to inform
weather-triggered promotions.

---

## Part 1 — Data Pipeline (`pipeline/`)

Loads the full Citibike history from the S3 `tripdata` bucket into BigQuery,
reconciles two schema eras into one canonical view, and builds a partitioned
daily table joined to NYC weather on `date`.

- **Source:** S3 `tripdata` bucket only — NYC annual/monthly files **and** the
  separate Jersey City files (region assigned by file source, not coordinates).
- **Unified view:** `trips_all` reconciles legacy (2013–2020) + new (2021+)
  schemas; `daily_summary` → one row per day × region × rider × bike type.
- **Materialized table:** `daily_summary_mat`, partitioned by month, clustered
  by region + rider type.
- **Weather join:** `nyu-datasets.weather.m_weather_daily_nyc`.
- **Fallback:** `nyu-datasets.citibike.m_daily_trips` when the local table is absent.
- **Verification:** `pipeline/reconciliation.md` — monthly counts vs
  `nyu-datasets.citibike`, **0 unexplained defects** (no month missing/double-counted).

Coverage: 2013-06-01 → 2026-06-30 (NYC ≈ 309.5M trips, JC ≈ 6.3M).
Design decisions: `CLAUDE.md`. Rebuild instructions: `pipeline/README.md`.

---

## Part 2 — Streamlit Dashboard (`dashboard/`)

Public, interactive, designed for a journalist or city planner — explicitly
**not** a data analyst. Built from a spec (`streamlitspec.md`), defended in
`dashboard/DECISIONS.md`, and gated by `dashboard/check_correctness.py`.

### Business questions → views

| # | Question | View |
|---|----------|------|
| Q1 | Is a ridership change weather-driven or operational? | V1 — ridership over time, weather overlaid |
| Q2 | How does casual riders' weather sensitivity differ from members'? | V3 — member vs casual across weather bands |
| Q3 | Does a weather-triggered casual promo make sense? | V2 — rides vs temperature by rider type |
| Q4 | What does a typical weather day look like? | V4 — seasonality (month / day-of-week) |
| — | Is a move system-wide or one side of the river? | V5 — NYC vs Jersey City |

### Filters
Date range · rider type · weather band (cold <40°F / mild 40–60 / warm 60–75 /
hot >75°F) · precipitation (dry/rainy) · bike type (classic/e-bike, 2021+).

### Verification (`streamlitspec.md §6`, results in `dashboard/DECISIONS.md`)
- **Correctness** — `check_correctness.py` **28/28 pass**; member+casual+unknown = total and NYC+JC = total on every row.
- **Speed** — cached once with `@st.cache_data`; cold load ~10 s, interactions instant (no BigQuery re-query).
- **Reach** — public on Streamlit Community Cloud (URL above), no login.
- **Clarity** — every chart title states the claim it makes.

---

## Architecture & auth

- **App:** Streamlit (`dashboard/app.py`), single cached load of the joined daily table.
- **Auth:** `data.py` uses a service-account key from `st.secrets` on Streamlit
  Cloud, and Application Default Credentials locally / on Cloud Run. No key files in the repo.
- **Hosting:** Streamlit Community Cloud is the public front door. A Cloud Run
  image (`dashboard/Dockerfile`) also exists, but NYU's GCP org policy blocks
  unauthenticated Cloud Run, so it's used only for authenticated/proxy access.

### Run locally
```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py          # uses Application Default Credentials
python check_correctness.py   # 28/28 correctness gate
```

### Deploy to Streamlit Community Cloud
See the step-by-step in the deploy section; paste the service-account key in the
`[gcp_service_account]` format from `dashboard/.streamlit/secrets.toml.example`.

---

## Repository layout

```
pipeline/       # loaders, SQL views, materialized table, reconciliation
dashboard/      # Streamlit app, data loader, correctness gate, decisions memo
streamlitspec.md  # dashboard spec + Verify targets
Verify.md         # "done" targets
CLAUDE.md         # pipeline Specify decisions + cloud setup
```

*Built with Claude Code.*
