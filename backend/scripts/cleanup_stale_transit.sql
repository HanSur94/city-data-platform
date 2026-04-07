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
