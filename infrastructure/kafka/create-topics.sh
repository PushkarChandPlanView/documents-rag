#!/bin/bash
set -e

KAFKA_BOOTSTRAP=${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}
PARTITIONS=3
REPLICATION=1
RETENTION_MS=$((7 * 24 * 60 * 60 * 1000))   # 7 days
DLQ_RETENTION_MS=$((30 * 24 * 60 * 60 * 1000)) # 30 days

echo "Waiting for Kafka to be ready at ${KAFKA_BOOTSTRAP}..."
until kafka-topics --bootstrap-server "${KAFKA_BOOTSTRAP}" --list > /dev/null 2>&1; do
  echo "  Kafka not ready yet, waiting 5s..."
  sleep 5
done
echo "Kafka is ready."

create_topic() {
  local topic=$1
  local retention=$2
  if kafka-topics --bootstrap-server "${KAFKA_BOOTSTRAP}" --describe --topic "${topic}" > /dev/null 2>&1; then
    echo "Topic '${topic}' already exists, skipping."
  else
    kafka-topics \
      --bootstrap-server "${KAFKA_BOOTSTRAP}" \
      --create \
      --topic "${topic}" \
      --partitions "${PARTITIONS}" \
      --replication-factor "${REPLICATION}" \
      --config "retention.ms=${retention}" \
      --config "cleanup.policy=delete"
    echo "Created topic '${topic}' with ${PARTITIONS} partitions."
  fi
}

# Pipeline topics
create_topic "document_uploaded"       "${RETENTION_MS}"
create_topic "text_extracted"          "${RETENTION_MS}"
create_topic "document_chunked"        "${RETENTION_MS}"
create_topic "embeddings_generated"    "${RETENTION_MS}"
create_topic "summary_generated"       "${RETENTION_MS}"

# Dead letter queue
create_topic "dlq.document_errors"     "${DLQ_RETENTION_MS}"

echo "All Kafka topics created successfully."
