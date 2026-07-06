-- 02_daily_summary.sql — one row per (day, region, rider type, bike type).
-- region comes straight from trips_all (file source). rideable_type is only
-- present in the new schema (2021+); legacy rows report bike_type='unknown'.
CREATE OR REPLACE VIEW `msbai-dwd-aa13072.citibike.daily_summary` AS
SELECT
  DATE(started_at) AS trip_date,
  region,
  member_casual AS rider_type,
  CASE
    WHEN rideable_type IS NULL THEN 'unknown'
    WHEN LOWER(rideable_type) LIKE '%electric%' THEN 'electric'
    WHEN LOWER(rideable_type) LIKE '%classic%'
      OR LOWER(rideable_type) LIKE '%docked%'   THEN 'classic'
    ELSE 'unknown'
  END AS bike_type,
  COUNT(*) AS trip_count,
  ROUND(AVG(TIMESTAMP_DIFF(ended_at, started_at, SECOND) / 60.0), 2) AS avg_duration_min,
  ROUND(AVG(
    CASE WHEN start_lat IS NOT NULL AND end_lat IS NOT NULL
    THEN ST_DISTANCE(ST_GEOGPOINT(start_lng, start_lat),
                     ST_GEOGPOINT(end_lng, end_lat)) / 1000.0 END), 3) AS avg_distance_km
FROM `msbai-dwd-aa13072.citibike.trips_all`
WHERE started_at IS NOT NULL AND ended_at IS NOT NULL AND ended_at > started_at
GROUP BY 1, 2, 3, 4;
