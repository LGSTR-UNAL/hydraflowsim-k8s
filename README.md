# HydraFlowSim Kubernetes infrastructure

Kubernetes manifests for deploying the simulation services and their supporting components. The manifests do not build application images. Before syncing them, build and publish the required images from your own software repositories, then replace the example image references in the manifests with the published image names and tags.

## Images to provide

- `services/sim-workers-deployment.yaml`: worker image built from the worker software source.
- `services/sim-server-deployment.yaml`: server image built from the server software source.
- `services/sim-stats-deployment.yaml`: statistics service image built from its software source.
- `kafka/kafka-connect/resources/kafka-connect.yaml`: Kafka Connect image built from `kafka/kafka-connect/resources/connectors/Dockerfile`.

## Worker image contract

The worker image must define its own `ENTRYPOINT` or `CMD` to start the worker service; the Kubernetes manifest does not override the image startup command. The image must include the solver runtime or make it available at the configured `SIMULATOR_EXECUTABLE` path. `SIMULATOR_HOME` identifies the directory containing solver files or supporting assets. Update these values in `services/sim-workers-deployment.yaml` to match the image. The worker implementation is responsible for invoking the solver with the request input and handling its outputs. Solver-specific command-line arguments belong to that worker implementation and are not fixed by this infrastructure repository.

## Worker duration, message locks and shutdown

Set `group.share.record.lock.duration.ms` and `group.share.max.record.lock.duration.ms` in `kafka/resources/kafka.yaml`, and `terminationGracePeriodSeconds` in `services/sim-workers-deployment.yaml`, using measured simulation durations. Use average durations to size routine operation, and include the longest or otherwise extreme cases plus time for cleanup and shutdown. If a share record lock expires while a simulation is still running, Kafka may deliver that request to another worker. If the termination grace period is shorter than an in-flight simulation, Kubernetes may kill the worker before it finishes. The current values (`400000`, `600000`, and `600`) must be evaluated against the workload; they are not universal durations.

## Service interfaces

`apps/runtime-config.yaml` centralizes the default HTTP port, Kafka connection and topic names, S3 compatible endpoint and bucket names, and database endpoint and table name. The server, worker, statistics service, and bucket initialization job load these settings from the `hydraflowsim-runtime-config` ConfigMap. Database and object storage credentials remain in Kubernetes Secrets. The server image supplies its own startup command and listens on `PORT` (default `8000`); its Kubernetes Service and TCP readiness and liveness probes use that port. If you change the port, update the container and Service port declarations as well.

The service image contract is:

1. **Server:** supply its own HTTP routes and request format, accept requests on `PORT`, use the configured Kafka and object storage settings, and publish request records to the configured topics.
2. **Workers:** consume records from `REQUEST_TOPIC`, load the referenced input objects from `S3_REQUESTS_BUCKET` and `S3_RESOURCES_BUCKET`, execute the configured simulator, and publish outputs to `RESULTS_TOPIC`. `SIMULATION_STATUS_TOPIC` is optional; worker images that support status events can publish there. Database writes use the configured connection and table settings when implemented by the image.
3. **Statistics service:** connect to the configured relational database and use the schema expected by its image.

The ConfigMap uses `KAFKA_BOOTSTRAP_SERVERS` for the Kafka connection, `DB_*` for database settings, and holds the table names used by the Kafka Connect sink connectors. Kafka Connect reads those table names through its environment config provider. After changing a table value, restart the Kafka Connect pods so they reload the ConfigMap values. These settings are supplied to images; they do not change the images' code. Each supplied image must read the matching variables. The Kafka payload schema, S3 object key layout, and relational table schema are application contracts: the server, workers, statistics image, and Kafka Connect configuration must agree on them. This repository does not transform or validate those application payloads. Kafka messages use the embedded Connect JSON schema. The `fecha` field is a logical Kafka Connect Timestamp encoded as epoch milliseconds and records message creation time. When changing topics or the consumer group, also update the Kafka topic resources, connector configurations, and the lag query in `services/sim-workers-scaledobject.yaml`. When changing the database schema or table, update the worker, statistics image, and Kafka Connect configuration to match.

The `registry.example.com/your-project/...` values are examples and must be replaced before deployment. For a private registry, create the `reg-cred` image pull Secret in namespace `hydraflowsim` and provide credentials with access to all referenced images. If the images are public, remove the `imagePullSecrets` entries from the deployment manifests.

For example, build and publish the included Kafka Connect image with: `docker build -f kafka/kafka-connect/resources/connectors/Dockerfile -t REGISTRY/PROJECT/kafka-connect:4.2.0-jdbc10.9.4 .`, followed by `docker push` for that tag. Build and push the other images using the Dockerfiles and instructions in their respective software repositories.

## Object storage

The `rustfs-secret-generator` Job creates `rustfs-credentials` in namespace `hydraflowsim` when it is absent, using random credentials stored only in the Kubernetes Secret. The RustFS application and services read `RUSTFS_ACCESS_KEY` and `RUSTFS_SECRET_KEY` from it. A CronJob checks every five minutes that the Secret still exists. The bucket initialization job creates `hydraflowsim-requests`, `hydraflowsim-resources`, and `hydraflowsim-results`.


## Result retries and database migration

The existing result sink now uses JDBC upserts with key
`(simulation_id, measurement)`, matching the peak-result payload. Before syncing
this connector in an existing installation, follow
[postgres/migrations/README.md](postgres/migrations/README.md) to add the unique
index without deleting records or resetting Kafka offsets. The migration stops
if duplicate keys require review. This prevents duplicate persisted peaks on
redelivery; it does not provide exactly-once simulator execution.

Time-series simulators need a different key that also identifies each sample.
Update the existing connector, its table schema and unique index together;
never apply the default peak key to time-series measurements.

## Monitoring and simulator changes

The existing Grafana dashboard includes desired/current/available worker replicas,
total worker CPU and memory, and CPU and memory per worker. Selectors target the
`sim-workers` Deployment and container in namespace `hydraflowsim`. CPU/memory
panels require Prometheus to scrape kubelet/cAdvisor metrics; replica panels need
kube-state-metrics. Missing measurements remain missing, rather than becoming zero.
The exporter and KEDA already reject failed, unavailable or stale lag observations.

To use a different simulator, update the existing server and worker images,
runtime ConfigMap, application schemas/connectors, and the existing ScaledObject
limits for that workload. Reuse Kafka, Kafka Connect, PostgreSQL, object storage,
exporter, dashboard and services. Do not install a second infrastructure stack or
copy a second set of simulator-specific Deployments. Experimental campaign Jobs,
cluster addresses, credentials and historical image tags from `yaluk-k8s-ops/dev`
are intentionally not copied into these generic manifests.

## Local verification

```sh
python3 -m unittest discover -s tests -v
python3 tests/generate_autoscaling_promql_test.py > /tmp/hydraflowsim-autoscaling.yaml
promtool test rules /tmp/hydraflowsim-autoscaling.yaml
```

The PromQL fixture generator requires PyYAML. The exporter tests cover Kafka
output parsing, unavailable/stale metrics, timeouts and Prometheus label escaping.


## User-defined database structure

A [manual PostgreSQL Job](jobs/postgres-sql/README.md) runs a user-provided
`schema.sql` to create application schemas and tables using the existing database
and credentials. It is not part of Argo CD synchronization; edit the SQL and run
`kubectl apply -k jobs/postgres-sql` explicitly. No additional infrastructure is
created, and the default SQL creates no application objects.


## Share-group exporter inputs and endpoints

The exporter runs `kafka-share-groups.sh` from `/opt/kafka/bin` and requires a
Kafka runtime with that command, Java, and Python. The supplied Strimzi image
provides them; no third-party Python packages are needed by the exporter.
The broker must support share groups and the selected group must exist.

| Environment variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `BOOTSTRAP_SERVERS` | yes | none | Kafka broker addresses |
| `SHARE_GROUP` | yes | none | Share group to query |
| `POLL_INTERVAL_SECONDS` | no | `30` | Delay between query starts, in seconds |
| `QUERY_TIMEOUT_SECONDS` | no | `20` | Maximum duration of each Kafka CLI query, in seconds |

Both timing values must be positive integers. HTTP binds to `0.0.0.0:9405`:
`GET /metrics` serves Prometheus text and `GET /healthz` reports process liveness.
Health does not assert successful Kafka communication. Failed or malformed queries
clear the cached rows; observations older than the polling interval plus query
timeout do not expose lag. Kafka's unavailable `-` values are not converted to
zero. `START-OFFSET` is exported separately and is never used as the lag.

Metrics: `kafka_sharegroup_lag`, `kafka_sharegroup_start_offset`,
`kafka_sharegroup_lag_available`, `kafka_sharegroup_exporter_scrape_success`,
`kafka_sharegroup_exporter_last_success_timestamp_seconds`, and
`kafka_sharegroup_exporter_errors_total`. All carry `consumergroup`; partition
metrics also carry `topic` and `partition`. The exporter does not add a namespace
label itself; Prometheus supplies it when scraping the Kubernetes workload.
