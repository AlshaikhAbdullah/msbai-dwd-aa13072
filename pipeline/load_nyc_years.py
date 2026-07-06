#!/usr/bin/env python3
"""
load_nyc_years.py — clean (re)load of NYC trip data for whole calendar years.

NYC packages history as annual zips (YYYY-citibike-tripdata.zip, 2013–2023) whose
months are split into multiple CSV parts. The original ad-hoc ingest mixed these
with the bigquery-public-data copy, which double-counted some 2017 months and
dropped others. This script reloads a year deterministically from the single
authoritative S3 annual zip: DELETE the year, then append every CSV part once.

Years 2013–2020 are legacy schema → trips_legacy. Pass years on argv, e.g.:
    python load_nyc_years.py 2013 2016 2017 2018
"""
import io
import os
import sys
import zipfile
import urllib.request

import pandas as pd
from google.cloud import bigquery

from load_jersey_city import LEGACY_SCHEMA, LEGACY_MAP, coerce, _norm  # reuse

PROJECT = "msbai-dwd-aa13072"
ANNUAL = "https://s3.amazonaws.com/tripdata/{y}-citibike-tripdata.zip"

def iter_csvs(zbytes):
    """Yield (name, DataFrame) for each real CSV part in an annual zip."""
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        for name in z.namelist():
            if name.startswith("__MACOSX") or not name.lower().endswith(".csv"):
                continue
            with z.open(name) as fh:
                yield name, pd.read_csv(fh, dtype=str, low_memory=False)

def main(years):
    c = bigquery.Client(project=PROJECT)
    tbl = f"{PROJECT}.citibike.trips_legacy"
    for y in years:
        y = int(y)
        print(f"\n=== {y} ===")
        # 1. delete the year (idempotent reload)
        c.query(f"DELETE FROM `{tbl}` "
                f"WHERE starttime >= '{y}-01-01' AND starttime < '{y+1}-01-01'"
                ).result()
        print(f"  deleted existing {y} rows")
        # 2. download annual zip
        raw = urllib.request.urlopen(ANNUAL.format(y=y), timeout=600).read()
        print(f"  downloaded {len(raw)/1e6:.0f} MB")
        # 3. load each CSV part
        total = 0
        for name, df in iter_csvs(raw):
            norm = {_norm(x) for x in df.columns}
            if not ("tripduration" in norm or "starttime" in norm):
                print(f"    skip non-legacy {name}")
                continue
            out = coerce(df, LEGACY_SCHEMA, LEGACY_MAP)
            c.load_table_from_dataframe(
                out, tbl,
                job_config=bigquery.LoadJobConfig(
                    write_disposition="WRITE_APPEND",
                    schema=[bigquery.SchemaField(n, t) for n, t in LEGACY_SCHEMA]),
            ).result()
            total += len(out)
        print(f"  loaded {total:,} rows for {y}")

if __name__ == "__main__":
    main(sys.argv[1:] or ["2013", "2016", "2017", "2018"])
