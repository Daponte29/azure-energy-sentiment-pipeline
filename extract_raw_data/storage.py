"""Helpers for landing RAW extracts in the Bronze zone (ADLS Gen2).

Bronze is immutable and replayable: every run writes a NEW, timestamped file
under a date-partitioned path and never overwrites. The source payload is stored
untouched — cleaning, dedup, scoring, and aggregation all happen later in the
Silver transform.

Path layout (Hive-style partitioning that ADF / Spark / DuckDB all understand):
    <dataset>/year=YYYY/month=MM/day=DD/<dataset>_<UTC-timestamp>.json

By default this uploads to the ADLS Gen2 container named by
AZURE_STORAGE_CONNECTION_STRING + AZURE_CONTAINER_NAME. For local testing, set
BRONZE_LOCAL_DIR to write the same layout to the local filesystem (no Azure).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings


def get_required_env(name: str) -> str:
    """Return an environment variable or exit with a clear message if missing."""
    value = os.getenv(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def bronze_blob_path(dataset: str, run_time: datetime | None = None) -> str:
    """Build the immutable, date-partitioned Bronze path for a dataset.

    >>> bronze_blob_path("news", datetime(2026, 6, 22, 17, 15, 1))
    'news/year=2026/month=06/day=22/news_20260622T171501Z.json'
    """
    ts = run_time or datetime.now(timezone.utc)
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc)
    return (
        f"{dataset}/year={ts:%Y}/month={ts:%m}/day={ts:%d}/"
        f"{dataset}_{ts:%Y%m%dT%H%M%S}Z.json"
    )


def write_bronze(
    records: list, dataset: str, run_time: datetime | None = None
) -> str:
    """Write a raw extract to Bronze and return the path written.

    Never overwrites (Bronze is immutable). If BRONZE_LOCAL_DIR is set, writes to
    the local filesystem for tests/local runs; otherwise uploads to ADLS Gen2.
    """
    path = bronze_blob_path(dataset, run_time)
    body = json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")

    local_dir = os.getenv("BRONZE_LOCAL_DIR")
    if local_dir:
        out = Path(local_dir) / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(body)
        print(f"[bronze:local] wrote {out} ({len(records)} records)")
        return str(out)

    connection_string = get_required_env("AZURE_STORAGE_CONNECTION_STRING")
    container_name = get_required_env("AZURE_CONTAINER_NAME")
    service_client = BlobServiceClient.from_connection_string(connection_string)
    try:
        service_client.create_container(container_name)
    except ResourceExistsError:
        pass  # Already exists, which is fine.

    blob_client = service_client.get_blob_client(container=container_name, blob=path)
    # overwrite=False enforces immutability: a timestamped path should never
    # already exist, and we want a hard error if it somehow does.
    blob_client.upload_blob(
        body,
        overwrite=False,
        content_settings=ContentSettings(content_type="application/json"),
    )
    print(f"[bronze] uploaded {path} to '{container_name}' ({len(records)} records)")
    return path
