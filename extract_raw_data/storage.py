"""Shared helpers for landing JSON files in Azure Blob Storage.

Both extract scripts (fetch_news.py, fetch_co2.py) write to the same
container under different prefixes (news/, co2/), mirroring the /raw/news/ and
/raw/co2/ layout in the pipeline design.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings


def get_required_env(name: str) -> str:
    """Return an environment variable or exit with a clear message if missing."""
    value = os.getenv(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def upload_json_file(file_path: Path, prefix: str) -> None:
    """Upload a local JSON file to Blob Storage under '<prefix>/<filename>'.

    Reads AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME from the
    environment. Creates the container if it does not already exist.
    """
    connection_string = get_required_env("AZURE_STORAGE_CONNECTION_STRING")
    container_name = get_required_env("AZURE_CONTAINER_NAME")

    service_client = BlobServiceClient.from_connection_string(connection_string)

    try:
        service_client.create_container(container_name)
        print(f"Created container '{container_name}'.")
    except ResourceExistsError:
        pass  # Already exists, which is fine.

    blob_name = f"{prefix.strip('/')}/{file_path.name}"
    blob_client = service_client.get_blob_client(container=container_name, blob=blob_name)
    with file_path.open("rb") as data:
        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )

    print(f"Uploaded {blob_name} to container '{container_name}'.")
