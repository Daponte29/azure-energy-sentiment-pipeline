"""Azure Functions entry point — timer-triggered serverless ingestion.

Two timers run the existing ingestion scripts on a schedule (the "Lambda
equivalent" of this pipeline):
    news_ingest  - hourly  (%NEWS_SCHEDULE%)  -> fetch_news.main()
    co2_ingest   - monthly (%CO2_SCHEDULE%)   -> fetch_co2.main()

The fetch_news / fetch_co2 / storage modules are copied into this folder at
deploy time (see deploy step). Config (NEWS_API_KEY, AZURE_STORAGE_CONNECTION_STRING,
AZURE_CONTAINER_NAME, DATA_DIR) comes from the Function App's application settings.
"""

import logging

import azure.functions as func

import fetch_co2
import fetch_news

app = func.FunctionApp()


@app.timer_trigger(
    schedule="%NEWS_SCHEDULE%", arg_name="timer",
    run_on_startup=False, use_monitor=True,
)
def news_ingest(timer: func.TimerRequest) -> None:
    logging.info("News ingestion: start")
    fetch_news.main()
    logging.info("News ingestion: done")


@app.timer_trigger(
    schedule="%CO2_SCHEDULE%", arg_name="timer",
    run_on_startup=False, use_monitor=True,
)
def co2_ingest(timer: func.TimerRequest) -> None:
    logging.info("CO2 ingestion: start")
    fetch_co2.main()
    logging.info("CO2 ingestion: done")
