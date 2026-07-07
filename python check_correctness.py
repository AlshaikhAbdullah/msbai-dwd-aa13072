"""
check_correctness.py — reconciles the dashboard's cached dataframe against the
source daily table for a random sample of dates.

Run locally BEFORE deploying:  python check_correctness.py
Requires the same ADC auth the app uses (gcloud auth application-default login).

This imports load_data() from app.py so it checks the EXACT dataframe the
dashboard serves — not a re-derivation that could drift from it.
"""

import random
import sys

from google.cloud import bigquery

# Pull the dashboard's own loader so we test what users actually see.
# If your app exposes the cached frame differently, adjust this import.
from app import load_data

PROJECT = "msbai-dwd-aa13072"
SOURCE_TABLE = "nyu-datasets.citibike.m_daily_trips"

# Columns to reconcile: dashboard column name -> source table column name.
# Adjust the right-hand side if your source schema uses different names.
COLUMNS = {
    "total":  "num_member_trips + num_casual_trips",
    "member": "num_member_trips",
    "casual": "num_casual_trips",
    "nyc":    "num_nyc_trips",
    "jc":     "num_jc_trips",
}

N_DATES = 5
INT_TOLERANCE = 0  # integer counts must match exactly


def source_values(client, date_str):
    """Query the source table directly for one date."""
    select = ", ".join(f"{expr} AS {alias}" for alias, expr in COLUMNS.items())
    sql = f"""
        SELECT {select}
        FROM `{SOURCE_TABLE}`
        WHERE date = DATE('{date_str}')
    """
    rows = list(client.query(sql).result())
    if not rows:
        return None
    r = rows[0]
    return {alias: r[alias] for alias in COLUMNS}


def dashboard_values(df, date_str):
    """Read the same numbers from the dashboard's cached dataframe."""
    row = df[df["date"].astype(str) == date_str]
    if row.empty:
        return None
    row = row.iloc[0]
    return {
        "total":  int(row["num_member_trips"]) + int(row["num_casual_trips"]),
        "member": int(row["num_member_trips"]),
        "casual": int(row["num_casual_trips"]),
        "nyc":    int(row["num_nyc_trips"]),
        "jc":     int(row["num_jc_trips"]),
    }


def main():
    client = bigquery.Client(project=PROJECT)
    df = load_data()

    all_dates = sorted(df["date"].astype(str).unique())
    sample = random.sample(all_dates, min(N_DATES, len(all_dates)))

    overall_pass = True
    for d in sample:
        src = source_values(client, d)
        dash = dashboard_values(df, d)

        if src is None or dash is None:
            print(f"[FAIL] {d}: date missing in {'source' if src is None else 'dashboard'}")
            overall_pass = False
            continue

        mismatches = [
            f"{k}: source={src[k]} dash={dash[k]}"
            for k in COLUMNS
            if abs((src[k] or 0) - (dash[k] or 0)) > INT_TOLERANCE
        ]

        if mismatches:
            print(f"[FAIL] {d}: " + "; ".join(mismatches))
            overall_pass = False
        else:
            print(f"[PASS] {d}: total={dash['total']:,} "
                  f"(member={dash['member']:,} casual={dash['casual']:,} "
                  f"nyc={dash['nyc']:,} jc={dash['jc']:,})")

    print("\n" + ("ALL PASS — numbers reconcile to source." if overall_pass
                  else "FAILURES above — do not deploy until resolved."))
    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
