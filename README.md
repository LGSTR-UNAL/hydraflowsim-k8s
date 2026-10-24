# HydraFlowSim Kubernetes infrastructure

Kubernetes manifests for deploying the simulation services and their supporting components. The manifests do not build application images. Before syncing them, build and publish the required images from your own software repositories, then replace the example image references in the manifests with the published image names and tags.

## Images to provide

- `services/sim-workers-deployment.yaml`: worker image built from the worker software source.
- `services/sim-server-deployment.yaml`: server image built from the server software source.
- `services/sim-stats-deployment.yaml`: statistics service image built from its software source.
- `kafka/kafka-connect/resources/kafka-connect.yaml`: Kafka Connect image built from `kafka/kafka-connect/resources/connectors/Dockerfile`.

## Worker image contract

The worker image must define its own `ENTRYPOINT` or `CMD` to start the worker service; the Kubernetes manifest does not override the image startup command. The image must include the solver runtime or make it available at the configured `SIMULATOR_EXECUTABLE` path. `SIMULATOR_HOME` identifies the directory containing solver files or supporting assets. Update these values in `services/sim-workers-deployment.yaml` to match the image. The worker implementation is responsible for invoking the solver with the request input and handling its outputs. Solver-specific command-line arguments belong to that worker implementation and are not fixed by this infrastructure repository.

The `registry.example.com/your-project/...` values are examples and must be replaced before deployment. For a private registry, create the `reg-cred` image pull Secret in namespace `hydraflowsim` and provide credentials with access to all referenced images. If the images are public, remove the `imagePullSecrets` entries from the deployment manifests.

For example, build and publish the included Kafka Connect image with: `docker build -f kafka/kafka-connect/resources/connectors/Dockerfile -t REGISTRY/PROJECT/kafka-connect:4.2.0-jdbc10.9.4 .`, followed by `docker push` for that tag. Build and push the other images using the Dockerfiles and instructions in their respective software repositories.

## Object storage

The `rustfs-secret-generator` Job creates `rustfs-credentials` in namespace `hydraflowsim` when it is absent, using random credentials stored only in the Kubernetes Secret. The RustFS application and services read `RUSTFS_ACCESS_KEY` and `RUSTFS_SECRET_KEY` from it. A CronJob checks every five minutes that the Secret still exists. The bucket initialization job creates `hydraflowsim-requests`, `hydraflowsim-resources`, and `hydraflowsim-results`.
