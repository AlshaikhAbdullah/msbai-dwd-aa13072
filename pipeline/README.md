# Citibike pipeline

Loads the full Citibike trip history (NYC + Jersey City, 2013-06 → present) into
BigQuery, reconciles two schema eras into one canonical view, and builds a
partitioned daily summary table. All design decisions are recorded in the root
`CLAUDE.md`.

## Data flow

```
S3 tripdata bucket
  ├─ YYYY-citibike-tripdata.zip (annual, 2013–2023)  ─┐
  ├─ YYYYMM-citibike-tripdata.zip (monthly, 2024+)   ─┼─▶ trips_legacy / trips_new   (NYC, by file source)
  └─ JC-YYYYMM-citibike-tripdata.csv.zip             ──▶ trips_jc_legacy / trips_jc_new (JC, by file source)
                                                               │
                          region stamped from source ──────────┤
                                                               ▼
                                              trips_all  (canonical unified VIEW)
                                                               ▼
                                              daily_summary  (VIEW: day × region × rider × bike)
                                                               ▼
                                    daily_summary_mat (TABLE, partitioned by month, clustered)
```

## Scripts

| File | Purpose | Idempotent? |
|------|---------|-------------|
| `load_jersey_city.py` | Load all JC files → `trips_jc_legacy`, `trips_jc_new` | Yes (drops+recreates) |
| `load_nyc_years.py` | (Re)load NYC annual zips by year → `trips_legacy` | Yes (delete-year + append) |
| `sql/01_trips_all.sql` | Canonical unified view + `region` | Yes (`CREATE OR REPLACE`) |
| `sql/02_daily_summary.sql` | Daily summary view | Yes |
| `sql/03_daily_summary_mat.sql` | Materialized partitioned table | Yes |
| `reconcile.py` | Verify vs `nyu-datasets.citibike`; writes `reconciliation.md` | Yes |

## Rebuild from scratch

```bash
# 1. raw loads (run once; each is idempotent)
python load_jersey_city.py
python load_nyc_years.py 2013 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023

# 2. views + materialized table (apply in order)
bq query --use_legacy_sql=false < sql/01_trips_all.sql
bq query --use_legacy_sql=false < sql/02_daily_summary.sql
bq query --use_legacy_sql=false < sql/03_daily_summary_mat.sql

# 3. verify
python reconcile.py   # -> reconciliation.md
```

Auth: relies on Application Default Credentials (the session service account);
no key file is read by these scripts.
