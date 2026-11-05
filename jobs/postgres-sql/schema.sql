-- Replace this file with your application DDL before running the Job.
-- Keep credentials and other secrets out of SQL files committed to Git.
-- This default is deliberately a no-op and creates no application objects.
SELECT current_database() AS database, current_user AS executed_by;

-- Example (uncomment and adapt):
-- CREATE SCHEMA IF NOT EXISTS my_simulator;
-- CREATE TABLE IF NOT EXISTS my_simulator.simulations (
--     id uuid PRIMARY KEY,
--     status text NOT NULL,
--     created_at timestamptz NOT NULL DEFAULT now()
-- );
