# RECENTLY COMPLETED

* Renamed `ingestion/` -> `extract_raw_data/` (all refs refactored; timer functions
  `news_extract`/`co2_extract`).
* `queries.py` — DuckDB ad-hoc SQL with a `--blob` toggle (local `data/` vs. live container).
* `PROJECT_FLOW_CHART.drawio` rebuilt to the **medallion** flow.
* Prod is quiescent (\~$0): ADF triggers already paused **and** prod Function App stopped.
* **Architecture decided:** medallion (Bronze/Silver on ADLS Gen2), transform via **Azure
  Function**; dev/prod environment separation with dev-first promotion.
* **Phase 0 (structure, not architecture) — DONE** on branch `feature/medallion-pipeline`:
  * Extracted all Terraform into `terraform/modules/pipeline/` (parameterized by `environment`,
    no provider/backend in the module).
  * Created `terraform/environments/dev/` (own state `dev/energynews.tfstate`).
  * `terraform apply` succeeded → `rg-energynews-dev` live (14 resources, \~$0 idle).
  * Removed obsolete ADF triggers — they referenced clickops-authored pipelines that don't
    exist in a fresh dev factory (a reproducibility gap dev-first exposed).

# NEXT STEPS

* **Commit** this Phase 0 checkpoint (then continue slowly).
* **Phase 1 — Bronze:** refactor the extract Function to extract-only + **immutable,
  date-partitioned raw writes**; enable **ADLS Gen2 (**`is_hns_enabled`) on the data storage
  (safe to recreate in ephemeral dev); add a **local fake-data test harness** ($0 validation).
* **Phase 2 — Silver:** ADF orchestrates a transform Function (clean/dedupe/VADER/aggregate)
  \-> Delta (delta-rs)/Parquet with MERGE. **Bring ADF pipelines into IaC** so envs reproduce.
* **Phase 3 — Serving:** Silver -> Dataverse upsert (deterministic GUIDs) via ADF.
* **Phase 4 — Promote:** create `environments/prod` (+ relocate orphaned `terraform/backend.tf`),
  parameterize CI (terraform + function deploy) for dev->prod on merge to `main`.
* **Discord alert test in dev:** separate dev channel/webhook or direct webhook POST.


