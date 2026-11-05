# PostgreSQL migrations

Run `001_simulation_results_idempotency.sql` against database `app` before
applying the `simulation-results-connector` upsert configuration. The migration
checks for duplicate natural keys and stops without deleting data if any exist.
Review and resolve such duplicates before retrying. Index creation is concurrent
because the results table can contain tens of millions of rows.

The connector then upserts each peak by `(simulation_id, measurement)`, making a
worker retry safe for already delivered result messages.

This migration targets the default `streaming."simulation-results"` table. If
`CONNECT_TABLE_SIMULATION_RESULTS` is changed, adapt the migration to that table.
Run it outside a transaction: `CREATE INDEX CONCURRENTLY` cannot run inside one.
The default natural key is suitable for one peak value per simulation and
measurement. For simulator time series, include the sample time or sample index
in both the unique key and connector `pk.fields`, otherwise upserts overwrite
samples. Do not use this two-column key for ParaEMT time-series results.

For an existing installation, pause `simulation-results-connector`, check/create
the index, then update and resume that same connector. Do not delete or recreate
the connector or reset its offsets. For a fresh database, create the application
table with its expected schema before running the migration. This SQL script is
manual and is not executed by Argo CD.
