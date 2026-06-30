# RECENTLY COMPLETED

- Prod quiescent (~$0): ADF triggers paused **and** prod Function App stopped.
- **Architecture decided:** medallion (Bronze/Silver on ADLS Gen2), transform via Azure
  Function; dev/prod environment separation with dev-first promotion.
- **Phase 0 (structure):** extracted Terraform into `modules/pipeline` (parameterized by
  `environment`); created `environments/dev` (own state); applied -> `rg-energynews-dev`.
  Renamed `ingestion/` -> `extract_raw_data/`. Removed obsolete clickops ADF triggers.
- **Phase 1 (Bronze) — built & tested in dev:**
  - Enabled **ADLS Gen2 (`is_hns_enabled`)** on the dev data lake.
  - Refactored extract to **extract-only + immutable, date-partitioned Bronze writes**
    (`storage.write_bronze`; news lands raw articles; co2 lands 3 raw tables). Committed.
  - **Dev integration test PASSED:** added News key to dev KV, deployed code to dev
    Function App, triggered `news_extract` + `co2_extract` via the admin endpoint, and
    verified raw data landed in dev ADLS Bronze (97 articles + co2_facility/sector/facts),
    fields confirmed untouched.

# NEXT STEPS

- **Observability (gap):** add `azurerm_application_insights` + wire the Function App's
  `APPLICATIONINSIGHTS_CONNECTION_STRING`. Today only live Streaming Logs exist — no
  persistent, KQL-queryable history (the real CloudWatch-Logs equivalent).
- **Phase 2 — Silver:** ADF orchestrates a transform Function (clean/dedupe/VADER/aggregate)
  -> Delta (delta-rs)/Parquet with MERGE; add **pytest** for the transform logic; bring ADF
  pipelines into IaC so envs reproduce.
- **Phase 3 — Serving:** Silver -> Dataverse upsert (deterministic GUIDs) via ADF.
- **Phase 4 — Promote:** create `environments/prod`; repoint CI (`terraform.yml` ->
  `environments/prod`, add plan-on-PR, fix `deploy-function.yml` per-env); relocate
  orphaned `terraform/backend.tf`.
- **Discord alert test in dev:** dev channel/webhook or direct webhook POST.
- **Teardown dev** (`terraform destroy`) between sessions to save credits.
- **Cleanup:** drop the now-unused `DATA_DIR` app setting (extract uploads from memory).
