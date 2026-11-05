# Run user-provided PostgreSQL DDL

This manual Job executes `schema.sql` against the existing database using
`hydraflowsim-runtime-config` (`DB_HOST`, `DB_PORT`, `DB_NAME`) and the existing
`postgres-app` Secret (`user`, `password`). It creates no database server, Kafka
service or additional application Deployment. The default SQL only reports the
current database/user; edit it to create the schemas and tables your simulator
requires. Object names and columns must agree with the existing service images
and Kafka Connect sink configuration.

## Run

Run from the repository root after the shared PostgreSQL infrastructure, runtime
ConfigMap and application Secret exist:

```sh
# First edit jobs/postgres-sql/schema.sql with your own DDL.
kubectl kustomize jobs/postgres-sql
kubectl apply -k jobs/postgres-sql
kubectl -n hydraflowsim wait --for=condition=complete job/postgres-user-schema --timeout=610s
kubectl -n hydraflowsim logs job/postgres-user-schema
```

The Job is intentionally outside all Argo CD Application paths and is not run by
a normal infrastructure sync. The SQL is mounted read-only via a generated
ConfigMap. Use ConfigMaps for small DDL files, not bulk data dumps or secrets.
The database role has the existing application's privileges, not superuser
privileges. Pin the PostgreSQL client image to a reviewed tag/digest as needed.

## Errors and repeat execution

`psql -X --set=ON_ERROR_STOP=1` ignores startup files and exits on the first SQL
error. The Job does not retry automatically (`backoffLimit: 0`), has a ten-minute
deadline and expires after one day. Increase `activeDeadlineSeconds` for long
index builds and adjust the wait timeout accordingly.

Statements already committed before an error are not rolled back automatically.
Prefer repeatable DDL (`IF NOT EXISTS` where appropriate). If your migration can
be atomic, add `BEGIN;` and `COMMIT;` in your SQL. Do not wrap
`CREATE INDEX CONCURRENTLY` in a transaction.

Check the previous Job has finished before rerunning. Delete only the completed
or failed Job, then apply the edited SQL again:

```sh
kubectl -n hydraflowsim get job postgres-user-schema
kubectl -n hydraflowsim logs job/postgres-user-schema
kubectl -n hydraflowsim delete job postgres-user-schema
kubectl apply -k jobs/postgres-sql
```

Do not delete a running Job to cancel SQL: database statements may already have
committed. Review the database state before rerunning. Old generated SQL
ConfigMaps may be deleted manually once no Job references them.

For the existing result-key migration, put the contents of
`postgres/migrations/001_simulation_results_idempotency.sql` into `schema.sql`,
follow the connector pause/resume procedure in the migration README and adjust
the deadline if required. Do not run this example migration until the target
application table exists and its key is appropriate for the simulator.
