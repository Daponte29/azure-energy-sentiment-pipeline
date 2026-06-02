"""Fetch EPA GHG emissions data, aggregate it, and land it in Azure Blob Storage.

Pipeline step 1 (CO2 source) of the Energy News Sentiment Pipeline:
    EPA Envirofacts  ->  clean + aggregate  ->  local /data/co2 JSON  ->  Blob (co2/)

Source: EPA Envirofacts GHG Reporting Program (keyless REST API).
    fact:      ghg.pub_facts_sector_ghg_emission  (facility x gas x subsector x year)
    facility:  ghg.pub_dim_facility               (facility_id -> state)
    sector:    ghg.pub_dim_sector                 (sector_id   -> sector_name)

Output grain: one record per (state x sector x year), summing co2e_emission across
all gases (CO2-equivalent). Matches the Dataverse `co2_emissions` table.

Required environment variables (loaded from a .env file in the project root):
    AZURE_STORAGE_CONNECTION_STRING
    AZURE_CONTAINER_NAME
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from storage import upload_json_file

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
MAX_RETRIES = 5   # transient network/DNS failures are common on long pulls
RETRY_BACKOFF = 2.0  # seconds, multiplied by attempt number

EMISSION_UNIT = "metric tons CO2e"
SOURCE_LABEL = "EPA Envirofacts GHGRP"

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "co2"


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
                wait = RETRY_BACKOFF * attempt
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


def build_facility_state_map() -> dict[int, dict]:
    """Map facility_id -> {state, state_name}, deduped across reporting years."""
    facilities = fetch_all_rows(FACILITY_TABLE)
    mapping: dict[int, dict] = {}
    for f in facilities:
        fid = f.get("facility_id")
        if fid is None:
            continue
        # State is stable per facility; keep the first non-null we see.
        if fid not in mapping or not mapping[fid].get("state"):
            mapping[fid] = {
                "state": f.get("state"),
                "state_name": f.get("state_name"),
            }
    print(f"Loaded {len(mapping)} facilities.")
    return mapping


def build_sector_name_map() -> dict[int, str]:
    """Map sector_id -> sector_name."""
    sectors = fetch_all_rows(SECTOR_TABLE)
    mapping = {s["sector_id"]: s.get("sector_name") for s in sectors if "sector_id" in s}
    print(f"Loaded {len(mapping)} sectors.")
    return mapping


def fetch_fact_rows() -> list[dict]:
    """Fetch all emission fact rows for the configured years."""
    all_rows: list[dict] = []
    for year in YEARS:
        year_rows = fetch_all_rows(f"{FACT_TABLE}/year/equals/{year}")
        print(f"  {year}: {len(year_rows)} fact rows")
        all_rows.extend(year_rows)
    return all_rows


def aggregate(
    fact_rows: list[dict],
    facility_state: dict[int, dict],
    sector_name: dict[int, str],
) -> list[dict]:
    """Sum co2e_emission by (state, sector, year) across all gases."""
    # key -> {"co2e": float, "facilities": set[int]}
    buckets: dict[tuple, dict] = defaultdict(lambda: {"co2e": 0.0, "facilities": set()})

    for row in fact_rows:
        fid = row.get("facility_id")
        sector_id = row.get("sector_id")
        year = row.get("year")
        emission = row.get("co2e_emission")
        if emission is None:
            continue

        loc = facility_state.get(fid, {})
        state = loc.get("state")
        state_name = loc.get("state_name")
        sector = sector_name.get(sector_id)

        key = (state, state_name, sector, year)
        buckets[key]["co2e"] += float(emission)
        buckets[key]["facilities"].add(fid)

    records: list[dict] = []
    for (state, state_name, sector, year), agg in buckets.items():
        records.append(
            {
                "state": state,
                "state_name": state_name,
                "sector": sector,
                "co2e_emission": round(agg["co2e"], 3),
                "emission_unit": EMISSION_UNIT,
                "facility_count": len(agg["facilities"]),
                "year": year,
                "recorded_at": f"{year}-01-01T00:00:00Z",
                "source": SOURCE_LABEL,
            }
        )

    # Stable, readable ordering: year, then state, then sector.
    records.sort(key=lambda r: (r["year"], r["state"] or "", r["sector"] or ""))
    return records


def save_local(records: list[dict]) -> Path:
    """Write the aggregated records to a timestamped JSON file under /data/co2."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = DATA_DIR / f"co2_emissions_{timestamp}.json"
    out_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(records)} aggregated records to {out_path}")
    return out_path


def main() -> None:
    load_dotenv()

    print(f"Fetching EPA GHG facts for years {YEARS[0]}-{YEARS[-1]}...")
    facility_state = build_facility_state_map()
    sector_name = build_sector_name_map()
    fact_rows = fetch_fact_rows()
    print(f"Total fact rows: {len(fact_rows)}")

    records = aggregate(fact_rows, facility_state, sector_name)
    if not records:
        print("No records produced; nothing to upload.")
        return

    out_path = save_local(records)
    upload_json_file(out_path, prefix="co2")
    print("Done.")


if __name__ == "__main__":
    main()
