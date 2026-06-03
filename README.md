# Azure Energy Sentiment Pipeline

A serverless data pipeline on Azure that tracks **public sentiment on solar, EV, and
nuclear energy** (news headlines scored with VADER) alongside **EPA CO₂e emissions**,
lands both in Dataverse, and surfaces them in Power BI — with a Discord alert when
sentiment turns sharply negative.

## Architecture

```
News API ─┐                                   ┌─ Power Automate → Discord alert
          │   Azure Functions    ADF          │   (sentiment < -0.3)
          ├─▶ (timer triggers) ─▶ pipelines ─▶ Dataverse ─┐
EPA API ──┘   → Blob Storage                              └─ Power BI dashboard
```

- **Ingestion** (`ingestion/`): Python scripts pull articles (scored with VADER) and EPA
  GHG data (aggregated by state × sector × year), then upload JSON to Blob Storage.
- **Serverless** (`functionapp/`): an Azure Function runs the scripts on a schedule
  (news hourly, CO₂ monthly).
- **Orchestration**: two Azure Data Factory pipelines load Blob → Dataverse (idempotent
  upserts on deterministic GUIDs).
- **Storage**: two Dataverse tables — `cp_climatenews` and `cp_co2emission`.
- **Alerting**: Power Automate posts to Discord on negative-sentiment articles.
- **Visualization**: Power BI connects directly to Dataverse.

## Tech stack

Python · Azure Functions · Blob Storage · Data Factory · Key Vault · Dataverse ·
Power Automate · Power BI · Terraform · GitHub Actions

## Infrastructure & CI/CD

All Azure infrastructure is defined in Terraform (`terraform/`) with remote state.
GitHub Actions deploys on push:

- changes under `terraform/**` → `terraform apply`
- changes under `ingestion/**` or `functionapp/**` → deploy to the Function App

Authentication to Azure uses OIDC federation (no stored credentials); secrets live in
Key Vault.

## Repo layout

```
ingestion/      fetch_news.py, fetch_co2.py, storage.py
functionapp/    Azure Functions timer triggers
terraform/      Azure infrastructure as code
dataverse/      Web API scripts to create the Dataverse tables
.github/        CI/CD workflows
```
