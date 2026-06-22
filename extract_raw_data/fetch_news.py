"""Fetch energy-related news articles, score them with VADER sentiment, and
land the result as a JSON file in Azure Blob Storage.

Pipeline step 1 (news source) of the Energy News Sentiment Pipeline:
    News API  ->  VADER scoring  ->  local /data/news JSON  ->  Blob (news/)

Output matches the Dataverse `climate_news` table: title, source, topic,
sentiment_compound, sentiment_label, published_at, url.

Required environment variables (loaded from a .env file in the project root):
    NEWS_API_KEY                    News API key (https://newsapi.org)
    AZURE_STORAGE_CONNECTION_STRING Azure Storage account connection string
    AZURE_CONTAINER_NAME            Target blob container, e.g. "climate-raw"
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv
from storage import get_required_env, upload_json_file
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# News API "everything" endpoint and the query that defines our topics.
# Quoted phrases + searchIn=title,description keep results on-topic (the
# unquoted OR query matched far too much loosely-related noise).
NEWS_API_URL = "https://newsapi.org/v2/everything"
QUERY = '"solar energy" OR "electric vehicle" OR "nuclear energy"'
PAGE_SIZE = 100  # max allowed on the News API free tier

# Fixed namespace for deterministic record IDs. A stable GUID per article means
# re-runs upsert the same Dataverse row (Upsert is the only write behavior the
# connector supports), so the pipeline is idempotent.
ID_NAMESPACE = uuid.UUID("5b8e7e2a-1f3c-4a6b-9d0e-7c2a4f6b8d1e")

# Keyword -> topic label, checked in order. First match wins.
TOPIC_KEYWORDS = [
    ("solar", ["solar"]),
    ("EV", ["electric vehicle", "electric car", " ev ", "ev,", "ev.", "e-car"]),
    ("nuclear", ["nuclear"]),
]

# Local staging dir for the JSON before upload. Overridable via DATA_DIR so the
# Azure Function can write to a writable temp path (the app folder is read-only).
DATA_DIR = (
    Path(os.environ["DATA_DIR"]) / "news"
    if os.getenv("DATA_DIR")
    else Path(__file__).resolve().parent.parent / "data" / "news"
)


def classify_topic(text: str) -> str:
    """Assign one of EV / solar / nuclear based on keywords, else 'general'."""
    lowered = f" {text.lower()} "
    for topic, keywords in TOPIC_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return topic
    return "general"


def sentiment_label(compound: float) -> str:
    """Bucket a VADER compound score using the standard +/-0.05 thresholds."""
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def fetch_articles(api_key: str) -> list[dict]:
    """Pull articles from the News API for the configured query."""
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


def score_articles(articles: list[dict]) -> list[dict]:
    """Extract fields, classify topic, and attach VADER sentiment + label."""
    analyzer = SentimentIntensityAnalyzer()
    scored: list[dict] = []

    for article in articles:
        title = article.get("title") or ""
        description = article.get("description") or ""
        url = article.get("url") or ""

        # Score title + description together for a fuller sentiment signal.
        text = f"{title}. {description}".strip()
        compound = analyzer.polarity_scores(text)["compound"]

        # Deterministic GUID (from the URL) so re-runs upsert the same row.
        record_id = str(uuid.uuid5(ID_NAMESPACE, url or title))

        scored.append(
            {
                "id": record_id,
                "title": title,
                "description": description,
                "source": (article.get("source") or {}).get("name"),
                "topic": classify_topic(text),
                "sentiment_compound": compound,
                "sentiment_label": sentiment_label(compound),
                "published_at": article.get("publishedAt"),
                "url": url,
            }
        )

    return scored


def save_local(scored: list[dict]) -> Path:
    """Write the scored articles to a single JSON file under /data/news.

    A fixed filename (overwritten each run) keeps exactly one file in the
    news/ blob prefix, so the ADF pipeline never reprocesses a growing pile.
    Dataverse still accumulates history via idempotent upserts on the GUIDs.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "news_latest.json"
    out_path.write_text(
        json.dumps(scored, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Saved {len(scored)} scored articles to {out_path}")
    return out_path


def main() -> None:
    load_dotenv()  # Load environment variables from .env file in the project root

    api_key = get_required_env("NEWS_API_KEY")

    articles = fetch_articles(api_key)
    if not articles:
        print("No articles returned; nothing to score or upload.")
        return

    scored = score_articles(articles)

    # Keep only clearly on-topic articles (solar / EV / nuclear); drop 'general'.
    on_topic = [r for r in scored if r["topic"] != "general"]
    print(f"Kept {len(on_topic)} of {len(scored)} articles after topic filter.")
    if not on_topic:
        print("No on-topic articles; nothing to upload.")
        return

    out_path = save_local(on_topic)
    upload_json_file(out_path, prefix="news")
    print("Done.")


if __name__ == "__main__":
    main()
