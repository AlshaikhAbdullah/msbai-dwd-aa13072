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
import re
import sys
import zipfile
import urllib.request
from collections import defaultdict

import pandas as pd
from google.cloud import bigquery

from load_jersey_city import LEGACY_SCHEMA, LEGACY_MAP, coerce, _norm  # reuse

PROJECT = "msbai-dwd-aa13072"
ANNUAL = "https://s3.amazonaws.com/tripdata/{y}-citibike-tripdata.zip"
_YM = re.compile(r"(\d{6})")

def _pick_csvs(names):
    """Annual zips often ship each month TWICE — a flat top-level
    `YYYYMM-citibike-tripdata.csv` AND nested `N_Month/..._1.csv` split parts.
    Loading both double-counts. Per month: keep the flat file if present, else
    fall back to the nested parts."""
    csvs = [n for n in names
            if n.lower().endswith(".csv") and not n.startswith("__MACOSX")]
    by_month = defaultdict(lambda: {"flat": [], "nested": []})
    for n in csvs:
        m = _YM.search(n.split("/")[-1])
        if not m:
            continue
        kind = "flat" if n.count("/") == 1 else "nested"
        by_month[m.group(1)][kind].append(n)
    chosen = []
    for ym, kinds in by_month.items():
        chosen += kinds["flat"] if kinds["flat"] else kinds["nested"]
    return chosen

def iter_csvs(zbytes):
    """Yield (name, DataFrame) for each deduped CSV part in an annual zip."""
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        for name in _pick_csvs(z.namelist()):
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
