# 0) create secret from the sample (edit keys first)
`kubectl apply -f deploy/gke/02-secret.yaml`

# 1) configmap with migrations
`kubectl apply -f deploy/gke/00-configmap-migrations.yaml`

# 2) persistent volume claim
`kubectl apply -f deploy/gke/01-pvc.yaml`

# 3) deployment (runs initContainer to apply migrations)
`kubectl apply -f deploy/gke/03-deployment.yaml`

# 4) service
`kubectl apply -f deploy/gke/04-service.yaml`

# 5 ) Ingress
Optional `kubectl apply -f deploy/gke/06-managed-cert.yaml`
Optional `kubectl apply -f deploy/gke/07-frontendconfig.yaml`
`kubectl apply -f deploy/gke/05-ingress-https.yaml`

## Notes

Ensure GKE StorageClass name matches standard-rwo (use `kubectl get storageclass` to confirm; change if needed).

## TODOs

- For public access, add an Ingress or switch Service type: LoadBalancer (then set externalTrafficPolicy: Local).

- Backups: use VolumeSnapshots or a CronJob that copies /data/raalisence.db to GCS.

- If we move to Postgres, drop the PVC and initContainer and switch envs to use RAAL_DB_DRIVER=pgx + RAAL_DB_DSN.