# yaluk-k8s-ops

## Object storage

The RustFS application and Yaluk services use the Kubernetes Secret `rustfs-credentials` in namespace `yaluk`. Provide the keys `RUSTFS_ACCESS_KEY` and `RUSTFS_SECRET_KEY` before syncing the application. The bucket initialization job creates `yaluk-requests`, `yaluk-resources`, and `yaluk-results`.
