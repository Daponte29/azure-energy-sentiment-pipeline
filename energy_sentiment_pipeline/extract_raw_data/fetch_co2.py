"""Extract step (Bronze) — fetch raw EPA GHGRP data and land each table as-is.

Source: EPA Envirofacts GHG Reporting Program (keyless REST API). Lands three
raw datasets in Bronze, untouched:
    co2_facts     - emission fact rows (facility x gas x subsector x year)
    co2_facility  - facility dimension (facility_id -> state)
    co2_sector    - sector dimension (sector_id   -> sector_name)

Joining, aggregating to (state x sector x year), and ID generation all happen
later in the Silver transform. Bronze stays a faithful, replayable copy.

Required environment variables (from a .env file in the project root):
    AZURE_STORAGE_CONNECTION_STRING
    AZURE_CONTAINER_NAME
"""

from __future__ import annotations

import time

import requests
from dotenv import load_dotenv

from storage import write_bronze

EFSERVICE_BASE = "https://data.epa.gov/efservice"
FACT_TABLE = "ghg.pub_facts_sector_ghg_emission"
FACILITY_TABLE = "ghg.pub_dim_facility"
SECTOR_TABLE = "ghg.pub_dim_sector"

# EPA reporting lags ~2 years; 2023 is currently the most recent available year.
YEARS = list(range(2019, 2024))  # 2019..2023 inclusive

# Rows requested per HTTP page. The pager advances by the count actually
# returned and stops on an empty page, so this is safe even if EPA caps lower.
PAGE_SIZE = 10000
MAX_PAGES = 1000  # safety valve against an unexpected infinite loop
MAX_RETRIES = 12  # this machine's DNS to data.epa.gov drops for minutes at a time
RETRY_BACKOFF = 5.0  # seconds * attempt, capped below, to outlast longer outages


def get_json(url: str) -> list:
    """GET a URL with retries/backoff to survive transient network/DNS blips."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            last_error = error
            if attempt < MAX_RETRIES:
                wait = min(RETRY_BACKOFF * attempt, 30)
                print(f"  request failed ({error.__class__.__name__}); "
                      f"retry {attempt}/{MAX_RETRIES - 1} in {wait:.0f}s")
                time.sleep(wait)
    raise last_error


def fetch_all_rows(path: str) -> list[dict]:
    """Page through an EPA efservice endpoint and return every row.

    `path` is everything between the base URL and the row-range segment, e.g.
    "ghg.pub_dim_sector" or "ghg.pub_facts_sector_ghg_emission/year/equals/2023".
    """
    rows: list[dict] = []
    start = 1
    for _ in range(MAX_PAGES):
        end = start + PAGE_SIZE - 1
        url = f"{EFSERVICE_BASE}/{path}/{start}:{end}/json"
        page = get_json(url)
        if not page:
            break
        rows.extend(page)
        start += len(page)
    return rows


def fetch_fact_rows() -> list[dict]:
    """Fetch all raw emission fact rows for the configured years."""
    all_rows: list[dict] = []
    for year in YEARS:
        year_rows = fetch_all_rows(f"{FACT_TABLE}/year/equals/{year}")
        print(f"  {year}: {len(year_rows)} fact rows")
        all_rows.extend(year_rows)
    return all_rows


def main() -> None:
    load_dotenv()

    print(f"Fetching EPA GHGRP raw data for years {YEARS[0]}-{YEARS[-1]}...")

    facilities = fetch_all_rows(FACILITY_TABLE)
    print(f"Fetched {len(facilities)} facility rows.")
    write_bronze(facilities, dataset="co2_facility")

    sectors = fetch_all_rows(SECTOR_TABLE)
    print(f"Fetched {len(sectors)} sector rows.")
    write_bronze(sectors, dataset="co2_sector")

    facts = fetch_fact_rows()
    print(f"Fetched {len(facts)} total fact rows.")
    write_bronze(facts, dataset="co2_facts")

    print("Done.")


if __name__ == "__main__":
    main()
