
## Pipeline — Specify decisions

Each row is a design decision and its one-line reason. Pipeline code lives in `pipeline/`.

| Decision | Choice | Reason |
|----------|--------|--------|
| Authoritative source | S3 `tripdata` bucket only (not `bigquery-public-data`) | Mixing the two double-counted 2017 and dropped other months; one source = no dupes/gaps |
| History range | 2013-06 → present, full history | Spec asks for the complete record |
| Region marker | By **file source** (NYC files vs `JC-*` files), stamped in `trips_all` | JC and Lower Manhattan share longitudes, so a coordinate cutoff mis-splits; the file family is unambiguous |
| Schema reconciliation | `trips_all` view unifies legacy (2013–2020, 15-col) + new (2021+, 13-col) into one column set | Two eras must be queryable as one canonical table |
| Rider type | Normalize `subscriber`/`customer` → `member`/`casual` | Legacy and new schemas name the same concept differently |
| Bike type | `rideable_type` → classic/electric; legacy rows = `unknown` | Bike type only exists in the new schema (2021+); don't fabricate it for older data |
| Distance | Haversine via `ST_DISTANCE` on start/end points, km | Trip distance isn't in the raw data; straight-line is the honest, reproducible proxy |
| Daily summary grain | One row per (`trip_date`, `region`, `rider_type`, `bike_type`) | Matches the slices the dashboard needs |
| Materialized table | `daily_summary_mat` partitioned by `DATE_TRUNC(trip_date, MONTH)`, clustered by `region, rider_type` | ~4,700 days exceed BigQuery's 4,000-partition cap, so month-partition the date column; cluster for common filters |
| Reconciliation source | `nyu-datasets.citibike.m_daily_trips` (`num_nyc_trips`, `num_jc_trips`) | Independent, per-region ground truth; evidence in `pipeline/reconciliation.md` |

### Pipeline layout
- `pipeline/load_jersey_city.py` — loads JC `JC-YYYYMM` files into `trips_jc_legacy` / `trips_jc_new`.
- `pipeline/load_nyc_years.py` — clean (re)load of NYC annual zips into `trips_legacy` (delete-year + append, idempotent).
- `pipeline/sql/01_trips_all.sql` — canonical unified view with `region`.
- `pipeline/sql/02_daily_summary.sql` — daily summary view.
- `pipeline/sql/03_daily_summary_mat.sql` — materialized, partitioned daily table.
- `pipeline/reconcile.py` → `pipeline/reconciliation.md` — independent-source verification.

## Cloud Credentials

**Provider:** GCP
**Project ID:** `msbai-dwd-aa13072`
**Service Account:** `claude-agent@msbai-dwd-aa13072.iam.gserviceaccount.com`

### Roles Granted

| Role | Justification |
|------|--------------|
| `roles/bigquery.dataEditor` | Create/write tables in the project's BigQuery datasets |
| `roles/bigquery.jobUser` | Execute BigQuery query jobs (required for reads and writes) |
| `roles/run.developer` | Deploy and manage the Cloud Run visualization website |
| `roles/storage.admin` | Create/manage GCS buckets and objects for build artifacts and static assets |

**Note:** `roles/bigquery.dataViewer` on `nyu-datasets` must be granted separately by the `nyu-datasets` project admin to allow reading `nyu-datasets.weather.m_weather_daily_nyc`.

### Per-User Credentials

Each team member has their own encrypted credentials file: `.cloud-credentials.<email>.enc`.
The encryption passphrase must be set as `GCP_CREDENTIALS_KEY` or `CLOUD_CREDENTIALS_KEY` in Claude Code on the Web environment variables.

Authentication is handled automatically at session start via `.claude/hooks/cloud-auth.sh`.

### Adding a New Team Member

Ask the agent: "Add me to the GCP credentials" — it will run the Add Team Member workflow.

### Escalating Permissions

If a command fails with a 403/access denied error, ask the agent: "Fix my GCP permissions" — it will identify the missing role and instruct the project owner to grant it.
