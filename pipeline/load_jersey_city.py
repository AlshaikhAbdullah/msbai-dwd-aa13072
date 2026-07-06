#!/usr/bin/env python3
"""
load_jersey_city.py — load the Jersey City Citibike trip files into BigQuery.

Why this exists: the main NYC ingest only pulled the NYC tripdata files. Jersey
City trips ship as SEPARATE files (JC-YYYYMM-citibike-tripdata.csv.zip) on the
same S3 bucket, so region must be assigned by FILE SOURCE, not by a coordinate
guess (JC and Lower Manhattan share nearly identical longitudes).

Loads into two raw tables mirroring the NYC schema exactly:
  citibike.trips_jc_legacy  (pre-2021 15-column schema)
  citibike.trips_jc_new     (2021+ 13-column schema)

Idempotent: both tables are truncated at the start of a run.
"""
import io
import sys
import zipfile
import urllib.request

import pandas as pd
from google.cloud import bigquery

PROJECT = "msbai-dwd-aa13072"
DATASET = "citibike"
BASE = "https://s3.amazonaws.com/tripdata/JC-{ym}-citibike-tripdata.csv.zip"

# Full JC history: launched 2015-09, through 2026-06 (last complete month).
def months(start=(2015, 9), end=(2026, 6)):
    y, m = start
    while (y, m) <= end:
        yield f"{y:04d}{m:02d}"
        m += 1
        if m > 12:
            y, m = y + 1, 1

LEGACY_SCHEMA = [
    ("tripduration", "INTEGER"), ("starttime", "TIMESTAMP"), ("stoptime", "TIMESTAMP"),
    ("start_station_id", "STRING"), ("start_station_name", "STRING"),
    ("start_lat", "FLOAT"), ("start_lng", "FLOAT"),
    ("end_station_id", "STRING"), ("end_station_name", "STRING"),
    ("end_lat", "FLOAT"), ("end_lng", "FLOAT"),
    ("bikeid", "STRING"), ("usertype", "STRING"),
    ("birth_year", "STRING"), ("gender", "STRING"),
]
NEW_SCHEMA = [
    ("ride_id", "STRING"), ("rideable_type", "STRING"),
    ("started_at", "TIMESTAMP"), ("ended_at", "TIMESTAMP"),
    ("start_station_name", "STRING"), ("start_station_id", "STRING"),
    ("end_station_name", "STRING"), ("end_station_id", "STRING"),
    ("start_lat", "FLOAT"), ("start_lng", "FLOAT"),
    ("end_lat", "FLOAT"), ("end_lng", "FLOAT"),
    ("member_casual", "STRING"),
]

def _norm(c: str) -> str:
    return "".join(ch for ch in c.lower() if ch.isalnum())

# Map normalized source header -> canonical target column.
LEGACY_MAP = {
    "tripduration": "tripduration",
    "starttime": "starttime", "stoptime": "stoptime",
    "startstationid": "start_station_id", "startstationname": "start_station_name",
    "startstationlatitude": "start_lat", "startstationlongitude": "start_lng",
    "endstationid": "end_station_id", "endstationname": "end_station_name",
    "endstationlatitude": "end_lat", "endstationlongitude": "end_lng",
    "bikeid": "bikeid", "usertype": "usertype",
    "birthyear": "birth_year", "gender": "gender",
}
NEW_MAP = {
    "rideid": "ride_id", "rideabletype": "rideable_type",
    "startedat": "started_at", "endedat": "ended_at",
    "startstationname": "start_station_name", "startstationid": "start_station_id",
    "endstationname": "end_station_name", "endstationid": "end_station_id",
    "startlat": "start_lat", "startlng": "start_lng",
    "endlat": "end_lat", "endlng": "end_lng",
    "membercasual": "member_casual",
}

def fetch_csv(ym: str):
    """Return list of DataFrames (one per CSV in the zip), or [] if the month 404s."""
    url = BASE.format(ym=ym)
    try:
        raw = urllib.request.urlopen(url, timeout=120).read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    frames = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv") or name.startswith("__MACOSX"):
                continue
            with z.open(name) as fh:
                frames.append(pd.read_csv(fh, dtype=str, low_memory=False))
    return frames

def coerce(df: pd.DataFrame, schema, colmap):
    src = {_norm(c): c for c in df.columns}
    out = pd.DataFrame()
    for norm_name, target in colmap.items():
        out[target] = df[src[norm_name]] if norm_name in src else None
    # Type coercion to match BQ schema
    for col, typ in schema:
        if col not in out.columns:
            out[col] = None
        if typ == "TIMESTAMP":
            out[col] = pd.to_datetime(out[col], errors="coerce", utc=True)
        elif typ == "FLOAT":
            out[col] = pd.to_numeric(out[col], errors="coerce")
        elif typ == "INTEGER":
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
        else:
            out[col] = out[col].astype("string")
    return out[[c for c, _ in schema]]

def main():
    c = bigquery.Client(project=PROJECT)
    # (Re)create empty target tables
    for tbl, schema in [("trips_jc_legacy", LEGACY_SCHEMA), ("trips_jc_new", NEW_SCHEMA)]:
        fqn = f"{PROJECT}.{DATASET}.{tbl}"
        c.query(f"DROP TABLE IF EXISTS `{fqn}`").result()
        bq_schema = [bigquery.SchemaField(n, t) for n, t in schema]
        c.create_table(bigquery.Table(fqn, schema=bq_schema))
        print(f"created {fqn}")

    legacy_rows = new_rows = 0
    for ym in months():
        frames = fetch_csv(ym)
        if not frames:
            print(f"  {ym}: (missing)")
            continue
        for df in frames:
            norm = {_norm(x) for x in df.columns}
            if "rideid" in norm:
                out, tbl, schema = coerce(df, NEW_SCHEMA, NEW_MAP), "trips_jc_new", NEW_SCHEMA
            elif "tripduration" in norm or "starttime" in norm:
                out, tbl, schema = coerce(df, LEGACY_SCHEMA, LEGACY_MAP), "trips_jc_legacy", LEGACY_SCHEMA
            else:
                print(f"  {ym}: UNKNOWN schema cols={list(df.columns)[:4]}")
                continue
            job = c.load_table_from_dataframe(
                out, f"{PROJECT}.{DATASET}.{tbl}",
                job_config=bigquery.LoadJobConfig(
                    write_disposition="WRITE_APPEND",
                    schema=[bigquery.SchemaField(n, t) for n, t in schema],
                ),
            )
            job.result()
            if tbl == "trips_jc_new":
                new_rows += len(out)
            else:
                legacy_rows += len(out)
        print(f"  {ym}: loaded ({len(frames)} file(s))")

    print(f"\nDONE  legacy={legacy_rows:,}  new={new_rows:,}  total={legacy_rows+new_rows:,}")

if __name__ == "__main__":
    sys.exit(main())
