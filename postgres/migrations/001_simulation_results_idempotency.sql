-- Make result upserts idempotent on the natural key emitted by the worker.
-- Run with psql -v ON_ERROR_STOP=1 -f before enabling the upsert connector.
-- This check preserves existing data and stops if duplicate keys need review first.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM streaming."simulation-results"
        GROUP BY simulation_id, measurement
        HAVING count(*) > 1
        LIMIT 1
    ) THEN
        RAISE EXCEPTION
            'Duplicate (simulation_id, measurement) rows exist; review them before creating the unique index';
    END IF;
END;
$$;

-- CONCURRENTLY avoids blocking inserts and reads while the index is built.
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
    simulation_results_simulation_id_measurement_uq
ON streaming."simulation-results" (simulation_id, measurement);
