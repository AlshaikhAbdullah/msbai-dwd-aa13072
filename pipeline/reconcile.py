#!/usr/bin/env python3
"""
reconcile.py — independent-source reconciliation of the loaded pipeline.

Compares our monthly trip counts (from the canonical trips_all view, unfiltered
so it is a like-for-like row count) against nyu-datasets.citibike.m_daily_trips,
split by region. Flags any month that is MISSING on either side or whose counts
diverge beyond tolerance (a sign of double-counting or a bad load).

Writes pipeline/reconciliation.md — the committed evidence.
"""
from google.cloud import bigquery

PROJECT = "msbai-dwd-aa13072"
TOL = 0.02  # 2% per-month tolerance (we drop invalid-timestamp rows; nyu keeps them)

SQL = """
WITH ours AS (
  SELECT DATE_TRUNC(DATE(started_at), MONTH) AS mon, region, COUNT(*) AS n
  FROM `msbai-dwd-aa13072.citibike.trips_all`
  WHERE started_at IS NOT NULL
  GROUP BY 1, 2
),
ours_p AS (
  SELECT mon,
         SUM(IF(region='New York City', n, 0)) AS our_nyc,
         SUM(IF(region='New Jersey',    n, 0)) AS our_jc
  FROM ours GROUP BY 1
),
theirs AS (
  SELECT DATE_TRUNC(date, MONTH) AS mon,
         SUM(num_nyc_trips) AS ref_nyc,
         SUM(num_jc_trips)  AS ref_jc
  FROM `nyu-datasets.citibike.m_daily_trips`
  GROUP BY 1
)
SELECT
  COALESCE(o.mon, t.mon) AS mon,
  IFNULL(o.our_nyc,0) our_nyc, IFNULL(t.ref_nyc,0) ref_nyc,
  IFNULL(o.our_jc,0)  our_jc,  IFNULL(t.ref_jc,0)  ref_jc
FROM ours_p o FULL OUTER JOIN theirs t USING (mon)
ORDER BY mon
"""

def pct(a, b):
    return abs(a - b) / b if b else (0.0 if a == 0 else 1.0)

def main():
    c = bigquery.Client(project=PROJECT)
    rows = list(c.query(SQL).result())

    bad = []
    tot_our_nyc = tot_ref_nyc = tot_our_jc = tot_ref_jc = 0
    for r in rows:
        tot_our_nyc += r.our_nyc; tot_ref_nyc += r.ref_nyc
        tot_our_jc  += r.our_jc;  tot_ref_jc  += r.ref_jc
        # A month present in the reference but absent for us (or vice versa)
        if (r.ref_nyc > 0 and r.our_nyc == 0) or (r.ref_jc > 0 and r.our_jc == 0):
            bad.append((r.mon, "MISSING", r))
        elif pct(r.our_nyc, r.ref_nyc) > TOL or pct(r.our_jc, r.ref_jc) > TOL:
            bad.append((r.mon, "DIVERGENT", r))

    lines = []
    lines.append("# Pipeline reconciliation vs `nyu-datasets.citibike`\n")
    lines.append(f"Independent source: `nyu-datasets.citibike.m_daily_trips` "
                 f"(`num_nyc_trips`, `num_jc_trips`).\n")
    lines.append("Our source: `msbai-dwd-aa13072.citibike.trips_all` (unfiltered row "
                 "counts), grouped by month and region.\n")
    lines.append("Query used: see `pipeline/reconcile.py`.\n")
    lines.append("## Totals\n")
    lines.append("| Region | Ours | Reference | Δ | Δ% |")
    lines.append("|---|--:|--:|--:|--:|")
    lines.append(f"| New York City | {tot_our_nyc:,} | {tot_ref_nyc:,} | "
                 f"{tot_our_nyc-tot_ref_nyc:,} | {100*pct(tot_our_nyc,tot_ref_nyc):.2f}% |")
    lines.append(f"| New Jersey | {tot_our_jc:,} | {tot_ref_jc:,} | "
                 f"{tot_our_jc-tot_ref_jc:,} | {100*pct(tot_our_jc,tot_ref_jc):.2f}% |")
    lines.append(f"\nMonths covered: {len(rows)}  "
                 f"({rows[0].mon} → {rows[-1].mon})\n")

    lines.append("## Months outside tolerance (±2%) or missing\n")
    if not bad:
        lines.append("**None — every month reconciles within 2% on both regions, "
                     "no month missing, no month double-counted.**\n")
    else:
        lines.append("| Month | Flag | Our NYC | Ref NYC | Our JC | Ref JC |")
        lines.append("|---|---|--:|--:|--:|--:|")
        for mon, flag, r in bad:
            lines.append(f"| {mon} | {flag} | {r.our_nyc:,} | {r.ref_nyc:,} | "
                         f"{r.our_jc:,} | {r.ref_jc:,} |")
        lines.append("")

    lines.append("## Full monthly detail\n")
    lines.append("| Month | Our NYC | Ref NYC | Our JC | Ref JC |")
    lines.append("|---|--:|--:|--:|--:|")
    for r in rows:
        lines.append(f"| {r.mon} | {r.our_nyc:,} | {r.ref_nyc:,} | {r.our_jc:,} | {r.ref_jc:,} |")

    out = "\n".join(lines) + "\n"
    with open("pipeline/reconciliation.md", "w") as fh:
        fh.write(out)

    print(f"NYC total diff: {100*pct(tot_our_nyc,tot_ref_nyc):.2f}%   "
          f"JC total diff: {100*pct(tot_our_jc,tot_ref_jc):.2f}%")
    print(f"{len(bad)} month(s) flagged. Wrote pipeline/reconciliation.md")

if __name__ == "__main__":
    main()
