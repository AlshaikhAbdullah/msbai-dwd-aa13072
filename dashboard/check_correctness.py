"""
Correctness gate for the dashboard.
Imports load_data from data.py (no Streamlit dependency).
All checks reconcile against the source BigQuery tables directly.
"""
import sys
import pandas as pd
from google.cloud import bigquery

PROJECT = "msbai-dwd-aa13072"
PASS, FAIL = "PASS", "FAIL"
results = []


def check(label: str, ok: bool, detail: str = ""):
    status = PASS if ok else FAIL
    results.append((status, label, detail))
    mark = "✅" if ok else "❌"
    print(f"{mark} [{status}] {label}" + (f"  →  {detail}" if detail else ""))


def bq():
    return bigquery.Client(project=PROJECT)


# ── 1. Load data ─────────────────────────────────────────────────────────────
print("\n── Loading data from data.py ──")
try:
    from data import _load_data_impl as load_data_plain
    df = load_data_plain()
    check("load_data returns a DataFrame", isinstance(df, pd.DataFrame))
    check("DataFrame is non-empty", len(df) > 0, f"{len(df):,} rows")
except Exception as e:
    check("load_data import and run", False, str(e))
    print("\nFATAL: cannot load data — aborting further checks.")
    sys.exit(1)

# ── 2. Required columns present ──────────────────────────────────────────────
print("\n── Column presence ──")
required_cols = [
    "date", "num_trips", "num_member_trips", "num_casual_trips",
    "num_nyc_trips", "num_jc_trips", "tavg_f", "prcp_inches",
    "is_rainy", "season", "is_weekend", "month", "day_of_week",
    "weather_band", "trips_7d",
]
for col in required_cols:
    check(f"column '{col}' present", col in df.columns)

# ── 3. Date range sanity ──────────────────────────────────────────────────────
print("\n── Date range ──")
min_date = df["date"].min()
max_date = df["date"].max()
check("Earliest date ≤ 2013-09-01", min_date <= pd.Timestamp("2013-09-01"),
      str(min_date.date()))
check("Latest date ≥ 2024-01-01",  max_date >= pd.Timestamp("2024-01-01"),
      str(max_date.date()))
check("No duplicate dates", df["date"].nunique() == len(df),
      f"{df['date'].nunique():,} unique / {len(df):,} rows")

# ── 4. member + casual = total ───────────────────────────────────────────────
print("\n── Rider-type arithmetic ──")
diff = (df["num_member_trips"] + df["num_casual_trips"] - df["num_trips"]).abs()
check(
    "member + casual == total (within 1 on every row)",
    (diff <= 1).all(),
    f"max deviation = {diff.max():.0f}",
)

# ── 5. NYC + JC ≈ total ──────────────────────────────────────────────────────
print("\n── Geography arithmetic ──")
geo_diff = (df["num_nyc_trips"] + df["num_jc_trips"] - df["num_trips"]).abs()
check(
    "nyc + jc == total (within 1 on every row)",
    (geo_diff <= 1).all(),
    f"max deviation = {geo_diff.max():.0f}",
)

# ── 6. Weather band coverage ─────────────────────────────────────────────────
print("\n── Weather bands ──")
check("No null weather_band", df["weather_band"].isna().sum() == 0,
      f"{df['weather_band'].isna().sum()} nulls")
check("All 4 bands present", set(df["weather_band"].cat.categories) == {
    "Cold (<40 °F)", "Mild (40–60 °F)", "Warm (60–75 °F)", "Hot (>75 °F)"
})

# ── 7. Reconcile total trips against the actual source used ──────────────────
print("\n── BQ reconciliation ──")
try:
    client = bq()
    df_total = int(df["num_trips"].sum())

    # Detect which source load_data used
    own_rows = list(client.query(
        "SELECT COUNT(*) AS n FROM `msbai-dwd-aa13072.citibike.daily_summary_mat`"
    ).result())[0].n
    use_own  = int(own_rows) > 0

    if use_own:
        # Reconcile against our mat joined to weather (exactly what load_data queries)
        bq_row = list(client.query("""
            SELECT SUM(t.trip_count) AS total
            FROM `msbai-dwd-aa13072.citibike.daily_summary_mat` t
            INNER JOIN `nyu-datasets.weather.m_weather_daily_nyc` w
              ON w.date = t.trip_date
        """).result())[0]
        source_label = "daily_summary_mat ⋈ weather"
    else:
        # Reconcile against nyu-datasets joined to weather
        bq_row = list(client.query("""
            SELECT SUM(c.num_trips) AS total
            FROM `nyu-datasets.citibike.m_daily_trips` c
            INNER JOIN `nyu-datasets.weather.m_weather_daily_nyc` w
              ON w.date = c.date
        """).result())[0]
        source_label = "m_daily_trips ⋈ weather"

    bq_total = int(bq_row.total)
    pct_diff = abs(bq_total - df_total) / bq_total * 100
    check(
        f"Total trips matches {source_label} within 0.5%",
        pct_diff < 0.5,
        f"df={df_total:,}  bq={bq_total:,}  diff={pct_diff:.4f}%",
    )
except Exception as e:
    check("BQ reconciliation query", False, str(e))

# ── 8. Spot-check a known date ────────────────────────────────────────────────
print("\n── Spot-check July 4 2024 ──")
row = df[df["date"] == "2024-07-04"]
check("July 4 2024 row exists", len(row) == 1)
if len(row) == 1:
    check("July 4 2024 num_trips > 0", int(row["num_trips"].iloc[0]) > 0,
          f"{int(row['num_trips'].iloc[0]):,} trips")
    check("July 4 2024 weather_band is Warm or Hot",
          row["weather_band"].iloc[0] in ("Warm (60–75 °F)", "Hot (>75 °F)"),
          str(row["weather_band"].iloc[0]))

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "─" * 50)
passes = sum(1 for s, _, _ in results if s == PASS)
fails  = sum(1 for s, _, _ in results if s == FAIL)
print(f"RESULT: {passes} passed, {fails} failed out of {len(results)} checks")
if fails:
    print("GATE: ❌ FAIL — do not deploy")
    sys.exit(1)
else:
    print("GATE: ✅ PASS — safe to deploy")
