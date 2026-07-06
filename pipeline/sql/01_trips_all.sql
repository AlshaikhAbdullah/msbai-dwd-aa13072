-- 01_trips_all.sql — canonical unified trip view.
-- Reconciles the two schema eras (legacy 2013–2020, new 2021+) into ONE column
-- set, and stamps region from FILE SOURCE (NYC files vs JC files), never from a
-- coordinate guess. usertype/member_casual normalized to member|casual.
CREATE OR REPLACE VIEW `msbai-dwd-aa13072.citibike.trips_all` AS
-- ── New York City: legacy schema ──────────────────────────────────────────
SELECT
  CAST(NULL AS STRING) AS ride_id,
  CAST(NULL AS STRING) AS rideable_type,
  starttime AS started_at, stoptime AS ended_at,
  start_station_name, start_station_id, end_station_name, end_station_id,
  start_lat, start_lng, end_lat, end_lng,
  CASE LOWER(usertype) WHEN 'subscriber' THEN 'member'
                       WHEN 'customer'   THEN 'casual'
                       ELSE LOWER(usertype) END AS member_casual,
  'New York City' AS region
FROM `msbai-dwd-aa13072.citibike.trips_legacy`
UNION ALL
-- ── New York City: new schema ─────────────────────────────────────────────
SELECT
  ride_id, rideable_type, started_at, ended_at,
  start_station_name, start_station_id, end_station_name, end_station_id,
  start_lat, start_lng, end_lat, end_lng,
  LOWER(member_casual) AS member_casual,
  'New York City' AS region
FROM `msbai-dwd-aa13072.citibike.trips_new`
UNION ALL
-- ── Jersey City: legacy schema ────────────────────────────────────────────
SELECT
  CAST(NULL AS STRING) AS ride_id,
  CAST(NULL AS STRING) AS rideable_type,
  starttime AS started_at, stoptime AS ended_at,
  start_station_name, start_station_id, end_station_name, end_station_id,
  start_lat, start_lng, end_lat, end_lng,
  CASE LOWER(usertype) WHEN 'subscriber' THEN 'member'
                       WHEN 'customer'   THEN 'casual'
                       ELSE LOWER(usertype) END AS member_casual,
  'New Jersey' AS region
FROM `msbai-dwd-aa13072.citibike.trips_jc_legacy`
UNION ALL
-- ── Jersey City: new schema ───────────────────────────────────────────────
SELECT
  ride_id, rideable_type, started_at, ended_at,
  start_station_name, start_station_id, end_station_name, end_station_id,
  start_lat, start_lng, end_lat, end_lng,
  LOWER(member_casual) AS member_casual,
  'New Jersey' AS region
FROM `msbai-dwd-aa13072.citibike.trips_jc_new`;
