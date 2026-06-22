# MAIN GOAL

Build a fully serverless, Infrastructure-as-Code Azure data pipeline that tracks
**public sentiment on solar, EV, and nuclear energy** (news headlines scored with
VADER) alongside **EPA CO₂e emissions**, lands both in Dataverse, surfaces them in
Power BI, and fires a Discord alert when sentiment turns sharply negative.

The deeper goal is hands-on practice with **Azure data-engineering best practices**
(transferring from AWS): Functions vs. Lambda, Blob/ADLS as a raw landing zone, Data
Factory orchestration, managed-identity + RBAC over stored keys, Key Vault secrets,
Terraform remote state, and OIDC-based CI/CD.

# RECENTLY DONE

- **Infra (Terraform + GitHub Actions, OIDC, remote state):** resource group
  `rg-energynews` (eastus2), storage `stenergynews1eelzy` (container `climate-raw`,
  prefixes `news/`, `co2/`), Function App `func-energynews-1eelzy` (Y1 Consumption,
  Python 3.11), Data Factory `adf-energynews-1eelzy`, Key Vault `kvenergynews1eelzy`.
  All access via system-assigned managed identities + RBAC — no stored keys.
- **Extract (`extract_raw_data/`):** `fetch_news.py` (News API → VADER sentiment +
  topic classify), `fetch_co2.py` (EPA GHGRP → aggregate by state × sector × year),
  `storage.py` (Blob upload helper). Both produce idempotent records (deterministic
  GUIDs) and land JSON in Blob. *Renamed from `ingestion/`.*
- **Serverless (`functionapp/`):** timer triggers `news_extract` (hourly) and
  `co2_extract` (monthly) run the extract scripts; secrets pulled from Key Vault.
- **Orchestration (ADF):** two published pipelines (`_pl_news_to_dataverse_`,
  `_pl_co2_to_dataverse_`) load Blob → Dataverse via idempotent upserts. Schedule
  triggers are defined in Terraform but **disabled** to save cost between demos.
- **Storage (Dataverse):** tables `cp_climatenews` and `cp_co2emission` created via
  the Web API (`dataverse/create_tables.py`); app user provisioned for ADF.
- **Alerting:** Power Automate → Discord webhook (KV secret `DISCORD-WEBHOOK-URL`)
  on sentiment < −0.3.
- **Local analysis:** `queries.py` runs ad-hoc DuckDB SQL over the local raw JSON.

# FLOWCHART

[PROJECT_FLOW_CHART.drawio](PROJECT_FLOW_CHART.drawio) — open with the
**Draw.io Integration** VS Code extension (diagrams.net).
