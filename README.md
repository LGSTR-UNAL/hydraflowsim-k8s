# HydraFlowSim Kubernetes infrastructure

Kubernetes manifests for deploying the simulation services and their supporting components. The manifests do not build application images. Before syncing them, build and publish the required images from your own software repositories, then replace the example image references in the manifests with the published image names and tags.

## Images to provide

- `services/sim-workers-deployment.yaml`: worker image built from the worker software source.
- `services/sim-server-deployment.yaml`: server image built from the server software source.
- `services/sim-stats-deployment.yaml`: statistics service image built from its software source.
- `kafka/kafka-connect/resources/kafka-connect.yaml`: Kafka Connect image built from `kafka/kafka-connect/resources/connectors/Dockerfile`.

## Worker image contract

The worker image must define its own `ENTRYPOINT` or `CMD` to start the worker service; the Kubernetes manifest does not override the image startup command. The image must include the solver runtime or make it available at the configured `SIMULATOR_EXECUTABLE` path. `SIMULATOR_HOME` identifies the directory containing solver files or supporting assets. Update these values in `services/sim-workers-deployment.yaml` to match the image. The worker implementation is responsible for invoking the solver with the request input and handling its outputs. Solver-specific command-line arguments belong to that worker implementation and are not fixed by this infrastructure repository.

## Service interfaces

`apps/runtime-config.yaml` centralizes the default HTTP port, Kafka connection and topic names, S3 compatible endpoint and bucket names, and database endpoint and table name. The server, worker, statistics service, and bucket initialization job load these settings from the `hydraflowsim-runtime-config` ConfigMap. Database and object storage credentials remain in Kubernetes Secrets. The server image supplies its own startup command and listens on `PORT` (default `8000`); its Kubernetes Service and TCP readiness and liveness probes use that port. If you change the port, update the container and Service port declarations as well.

The service image contract is:

1. **Server:** supply its own HTTP routes and request format, accept requests on `PORT`, use the configured Kafka and object storage settings, and publish request records to the configured topics.
2. **Workers:** consume records from `REQUEST_TOPIC`, load the referenced input objects from `S3_REQUESTS_BUCKET` and `S3_RESOURCES_BUCKET`, execute the configured simulator, publish outputs to `RESULTS_TOPIC` and, if status events are supported, `SIMULATION_STATUS_TOPIC`. Database writes use the configured connection and table settings when implemented by the image.
3. **Statistics service:** connect to the configured relational database and use the schema expected by its image.

The ConfigMap provides both `KAFKA_BOOTSTRAP_SERVERS` and `KAFKA_HOST`; all database connection settings use the `DB_*` prefix. These settings are supplied to images; they do not change the images' code. Each supplied image must read the matching variables. The Kafka payload schema, S3 object key layout, and relational table schema are application contracts: the server, workers, statistics image, and Kafka Connect configuration must agree on them. This repository does not transform or validate those application payloads. When changing topics or the consumer group, also update the Kafka topic resources, connector configurations, and the lag query in `services/sim-workers-scaledobject.yaml`. When changing the database schema or table, update the worker, statistics image, and Kafka Connect configuration to match.

The `registry.example.com/your-project/...` values are examples and must be replaced before deployment. For a private registry, create the `reg-cred` image pull Secret in namespace `hydraflowsim` and provide credentials with access to all referenced images. If the images are public, remove the `imagePullSecrets` entries from the deployment manifests.

For example, build and publish the included Kafka Connect image with: `docker build -f kafka/kafka-connect/resources/connectors/Dockerfile -t REGISTRY/PROJECT/kafka-connect:4.2.0-jdbc10.9.4 .`, followed by `docker push` for that tag. Build and push the other images using the Dockerfiles and instructions in their respective software repositories.

## Object storage

The `rustfs-secret-generator` Job creates `rustfs-credentials` in namespace `hydraflowsim` when it is absent, using random credentials stored only in the Kubernetes Secret. The RustFS application and services read `RUSTFS_ACCESS_KEY` and `RUSTFS_SECRET_KEY` from it. A CronJob checks every five minutes that the Secret still exists. The bucket initialization job creates `hydraflowsim-requests`, `hydraflowsim-resources`, and `hydraflowsim-results`.
