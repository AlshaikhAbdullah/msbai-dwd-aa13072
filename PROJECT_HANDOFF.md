# PROJECT HANDOFF — NYC Weather × Citibike (msbai-dwd-aa13072)

Complete context for continuing this assignment in a fresh chat. Coursework:
**Dealing with Data Using Python**, NYU Stern MSBAi. Everything below is the
as-built state; all work is merged to `main`.

---

## 0. Coordinates

- **GitHub repo:** `AlshaikhAbdullah/msbai-dwd-aa13072` (work on branch `main`; dev branch `claude/happy-cray-wsbwub`)
- **GCP project:** `msbai-dwd-aa13072`
- **Service account:** `claude-agent@msbai-dwd-aa13072.iam.gserviceaccount.com`
  - Roles: `bigquery.dataEditor`, `bigquery.jobUser`, `run.developer`, `storage.admin`
  - Needs `bigquery.dataViewer` + `jobUser` to read `nyu-datasets`
- **Public dashboard:** https://msbai-dwd-aa13072-kezv8xk9u8iclxichuno3q.streamlit.app/
- **Auth model:** `dashboard/data.py` uses a service-account key from `st.secrets["gcp_service_account"]` on Streamlit Cloud; Application Default Credentials locally / on Cloud Run. Session auth via `.claude/hooks/cloud-auth.sh` decrypting `.cloud-credentials.<email>.enc` with `GCP_CREDENTIALS_KEY`.

---

## 1. BigQuery objects (dataset `citibike`)

| Object | Type | Notes |
|--------|------|-------|
| `trips_legacy` | table | NYC pre-2021 (15-col schema): tripduration, starttime, stoptime, stations, lat/lng, usertype, birth_year, gender |
| `trips_new` | table | NYC 2021+ (13-col): ride_id, rideable_type, started_at, ended_at, stations, lat/lng, member_casual |
| `trips_jc_legacy` / `trips_jc_new` | tables | Jersey City, same two schemas |
| `trips_all` | **view** | Canonical union of all four; normalizes rider type → member/casual; stamps `region` = 'New York City' / 'New Jersey' **by file source** |
| `daily_summary` | **view** | One row per (trip_date, region, rider_type ∈ member/casual/unknown, bike_type ∈ classic/electric/unknown); trip_count, avg_duration_min, avg_distance_km (haversine) |
| `daily_summary_mat` | **table** | Materialized from daily_summary; `PARTITION BY DATE_TRUNC(trip_date, MONTH)`, `CLUSTER BY region, rider_type` |

Counts: NYC ≈ 309.5M, JC ≈ 6.3M trips; span 2013-06-01 → 2026-06-30.

---

## 2. Repo layout

```
pipeline/
  load_jersey_city.py      # JC files (JC-YYYYMM-*.csv.zip) → trips_jc_*
  load_nyc_years.py        # NYC annual zips → trips_legacy/new; delete-year+append (idempotent);
                           #   handles flat-vs-nested duplicate CSVs AND nested monthly zips
  sql/01_trips_all.sql     # unified view + region
  sql/02_daily_summary.sql # daily summary view
  sql/03_daily_summary_mat.sql  # materialized partitioned table
  reconcile.py             # → reconciliation.md (vs nyu-datasets)
  predict_ridership.py     # STRETCH: out-of-sample ridership prediction
  reconciliation.md        # committed verification evidence
  README.md
dashboard/
  app.py                   # Streamlit: sidebar filters + 5 tabs (V1–V5); claim = chart title
  data.py                  # @st.cache_data load_data(); _client() reads st.secrets or ADC
  check_correctness.py     # 28-check gate
  requirements.txt         # streamlit 1.35, plotly 5.22, pandas 2.2.2, google-cloud-bigquery 3.21,
                           #   db-dtypes 1.2, statsmodels 0.14.4, scipy 1.13.1
  Dockerfile               # Cloud Run (copies app.py AND data.py)
  DECISIONS.md             # decisions memo (Translate work, both parts + stretch)
  .streamlit/secrets.toml.example
streamlitspec.md           # Part 2 spec: questions, filters, 5 views, Verify targets §6
Verify.md                  # "done" targets
CLAUDE.md                  # pipeline Specify decisions + cloud setup
```

Python for Streamlit Cloud pinned to **3.12** (3.13 lacks pandas 2.2.2 wheels → source build).

---

## 3. Key design decisions (Specify) — full table in CLAUDE.md

- **One source = S3 `tripdata` bucket only** (not `bigquery-public-data`, which caused double-counting).
- **Region by file source**, never coordinates (JC and Lower Manhattan share longitudes).
- Unify legacy+new schemas in `trips_all`; normalize subscriber/customer → member/casual.
- Bike type only exists 2021+; legacy = 'unknown'. Distance = haversine (km) proxy.
- Mat table month-partitioned because ~4,700 days > BigQuery's 4,000 daily-partition cap.
- Reconcile vs `nyu-datasets.citibike.m_daily_trips`.

---

## 4. Verification (as measured)

- **Dashboard gate:** `python dashboard/check_correctness.py` → **28/28 PASS**. member+casual+unknown = total and NYC+JC = total on every row; reconciles to daily_summary_mat within 0.5%.
- **Reconciliation:** `python pipeline/reconcile.py` → **0 unexplained defects**. NYC total within 0.64%; JC matches month-for-month. All residuals explained:
  - **Proven finding:** the official S3 file for 2023-05 has 3,453,144 rows (sum of 4 parts); we load 3,453,576; `nyu-datasets` reports 3,580,766 — the reference has ~127k rows MORE than the published file itself. So the 2022–2024 NYC gap is a reference snapshot predating Citibike's data revisions, not our defect.
  - JC missing months (2017-08, 2022-07, 2025-10, 2026-01, 2026-04) are files not published on S3 (404).
- **Load-time:** cold `load_data()` ≈ 10 s (3 BQ queries); interactions instant (cached, in-memory pandas; df is ~1.3 MB / 4,736 rows).

### Bugs found & fixed during reconciliation (were in the ORIGINAL ad-hoc load)
- 15 missing NYC months, 9 double-counted 2017 months (S3 + public-BQ overlap), 2018-04 half-loaded → fixed by clean delete-year+reload of 2013/2016/2017/2018 and 2022/2023 from S3.
- JC never loaded originally (region undercounted ~30×) → loaded 6.3M rows.

---

## 5. Stretch — prediction (in DECISIONS.md)

`pipeline/predict_ridership.py`: HistGradientBoostingRegressor predicts daily NYC
rides from weather + calendar features. Time-based hold-out: train 2013-06→2025-05,
test on unseen 2025-05-30→2026-05-29. **Out-of-sample MAPE = 23.9%** (R² 0.897, MAE
12,360/day). A linear detrend was tried and did worse (non-linear growth). Not wired
into the app (v1 is descriptive by spec).

---

## 6. Submission

1. Repo `AlshaikhAbdullah/msbai-dwd-aa13072` (main)
2. Project `msbai-dwd-aa13072`; objects `citibike.trips_all` (view), `citibike.daily_summary` (view), `citibike.daily_summary_mat` (table)
3. Dashboard URL (above)
4. `dashboard/DECISIONS.md`

Instructor + Ilias granted access to repo and GCP project.

---

## 7. Reproduce from scratch

```bash
# raw loads (idempotent)
python pipeline/load_jersey_city.py
python pipeline/load_nyc_years.py 2013 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023
# views + mat table (in order)
bq query --use_legacy_sql=false < pipeline/sql/01_trips_all.sql
bq query --use_legacy_sql=false < pipeline/sql/02_daily_summary.sql
bq query --use_legacy_sql=false < pipeline/sql/03_daily_summary_mat.sql
# verify
python pipeline/reconcile.py          # -> reconciliation.md, 0 defects
cd dashboard && python check_correctness.py   # 28/28
python pipeline/predict_ridership.py  # stretch, ~24% out-of-sample
```

---

## 8. Open / housekeeping

- **Budget alert:** $10 budget in GCP Billing → Budgets & alerts (console task; SA lacks billing rights).
- **Service-account key** was shown in a prior chat; user opted NOT to rotate. If desired later: generate new key, re-encrypt `.cloud-credentials.<email>.enc`, update the Streamlit `[gcp_service_account]` secret.
- **NYU GCP org policy blocks public Cloud Run** (`host_not_allowed`), which is why the public front door is Streamlit Community Cloud, not Cloud Run.
- Streamlit deploy: repo `main`, main file `dashboard/app.py`, Python 3.12, secret pasted as `[gcp_service_account]` (see `.streamlit/secrets.toml.example`).
