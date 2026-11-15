-- One-time cleanup: delete transit features at POINT(0,0) without feature_type
-- These are stale trip_update placeholders from before the feature_type fix
-- Run once manually against the DB after deploying the gtfs_rt.py connector fix.
--
-- Usage:
--   psql -U citydata -d citydata -f backend/scripts/cleanup_stale_transit.sql
--
DELETE FROM features
WHERE domain = 'transit'
  AND ST_Equals(geometry, ST_GeomFromText('POINT(0 0)', 4326))
  AND (properties->>'feature_type') IS NULL;

-- ---------------------------------------------------------------------------
-- Optional manual cleanup after deploying the GTFS-RT bbox/relevance fix.
-- Review each statement before running; neither is run automatically.
-- ---------------------------------------------------------------------------

-- (a) Legacy per-trip placeholder features written by the old GTFS-RT connector
-- (one 'trip:{trip_id}' feature per trip update). Their transit_positions rows
-- cascade via the FK; bus_interpolation only reads the last 10 minutes of delays,
-- and new delays land on the single 'gtfs-rt:trip-updates' placeholder.
-- DELETE FROM features
-- WHERE domain = 'transit'
--   AND source_id LIKE 'trip:%';

-- (b) GTFS-RT vehicle features outside their town's bbox (the old connector stored
-- the whole Germany-wide feed). towns.bbox is the JSONB array
-- [lon_min, lat_min, lon_max, lat_max] written by main.py at startup.
-- DELETE FROM features f
-- USING towns t
-- WHERE f.town_id = t.id
--   AND f.domain = 'transit'
--   AND f.source_id LIKE 'vehicle:%'
--   AND NOT ST_Covers(
--         ST_MakeEnvelope(
--           (t.bbox->>0)::float8, (t.bbox->>1)::float8,
--           (t.bbox->>2)::float8, (t.bbox->>3)::float8, 4326),
--         f.geometry);
