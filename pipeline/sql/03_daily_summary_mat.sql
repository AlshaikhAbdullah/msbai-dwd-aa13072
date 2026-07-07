-- 03_daily_summary_mat.sql — materialized daily table built from the view.
-- Partitioned on trip_date. BigQuery caps a table at 4,000 partitions, and the
-- history spans ~4,700 days, so we partition by MONTH(trip_date) — the standard
-- workaround that keeps the partition column = the date and stays well under the
-- cap. Clustered by region + rider_type for the dashboard's common slices.
CREATE OR REPLACE TABLE `msbai-dwd-aa13072.citibike.daily_summary_mat`
PARTITION BY DATE_TRUNC(trip_date, MONTH)
CLUSTER BY region, rider_type AS
SELECT * FROM `msbai-dwd-aa13072.citibike.daily_summary`;
