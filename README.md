# yaluk-k8s-ops

## Object storage

The `rustfs-secret-generator` Job creates `rustfs-credentials` in namespace `yaluk` when it is absent, using random credentials stored only in the Kubernetes Secret. The RustFS application and Yaluk services read `RUSTFS_ACCESS_KEY` and `RUSTFS_SECRET_KEY` from it. A CronJob checks every five minutes that the Secret still exists. The bucket initialization job creates `yaluk-requests`, `yaluk-resources`, and `yaluk-results`.
