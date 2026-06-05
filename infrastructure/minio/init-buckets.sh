#!/bin/sh
set -e

MINIO_ENDPOINT=${MINIO_ENDPOINT:-minio:9000}
MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin}

echo "Waiting for MinIO to be ready at ${MINIO_ENDPOINT}..."
until mc alias set local "http://${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" > /dev/null 2>&1; do
  echo "  MinIO not ready yet, waiting 5s..."
  sleep 5
done
echo "MinIO is ready."

create_bucket() {
  local bucket=$1
  if mc ls "local/${bucket}" > /dev/null 2>&1; then
    echo "Bucket '${bucket}' already exists, skipping."
  else
    mc mb "local/${bucket}"
    echo "Created bucket '${bucket}'."
  fi
}

create_bucket "${MINIO_BUCKET_RAW:-documents-raw}"
create_bucket "${MINIO_BUCKET_PROCESSED:-documents-processed}"

echo "MinIO initialization complete."
