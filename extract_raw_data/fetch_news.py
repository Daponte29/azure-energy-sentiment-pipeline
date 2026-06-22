"""Extract step (Bronze) — fetch raw energy-news articles and land them as-is.

Pulls the News API "everything" endpoint and writes the raw article objects to
the Bronze zone, untouched. VADER scoring, topic classification, dedup, ID
generation, and filtering all happen later in the Silver transform — Bronze
stays a faithful, replayable copy of exactly what the API returned.

Required environment variables (from a .env file in the project root):
    NEWS_API_KEY                    News API key (https://newsapi.org)
    AZURE_STORAGE_CONNECTION_STRING Azure Storage account connection string
    AZURE_CONTAINER_NAME            Target ADLS Gen2 container, e.g. "climate-raw"
"""

from __future__ import annotations

import requests
from dotenv import load_dotenv

from storage import get_required_env, write_bronze

# News API "everything" endpoint and the query that defines our topics.
# Quoted phrases + searchIn=title,description keep results on-topic (the
# unquoted OR query matched far too much loosely-related noise).
NEWS_API_URL = "https://newsapi.org/v2/everything"
QUERY = '"solar energy" OR "electric vehicle" OR "nuclear energy"'
PAGE_SIZE = 100  # max allowed on the News API free tier


def fetch_articles(api_key: str) -> list[dict]:
    """Pull raw articles from the News API for the configured query."""
    params = {
        "q": QUERY,
        "searchIn": "title,description",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": PAGE_SIZE,
        "apiKey": api_key,
    }
    response = requests.get(NEWS_API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "ok":
        raise RuntimeError(
            f"News API error: {payload.get('code')} - {payload.get('message')}"
        )

    articles = payload.get("articles", [])
    print(f"Fetched {len(articles)} articles from the News API.")
    return articles


def main() -> None:
    load_dotenv()  # Load environment variables from .env in the project root

    api_key = get_required_env("NEWS_API_KEY")

    articles = fetch_articles(api_key)
    if not articles:
        print("No articles returned; nothing to land.")
        return

    write_bronze(articles, dataset="news")
    print("Done.")


if __name__ == "__main__":
    main()
