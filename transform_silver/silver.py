"""Silver transform — clean, dedupe, score, and conform raw Bronze records.

Pure functions (no Azure I/O) so they're fast to unit-test. The Bronze->Silver
Function wraps these with read/write later. This is the scoring/classification
logic that used to live in the extract step — it belongs here in Silver.
"""

from __future__ import annotations

import uuid

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Stable namespace so re-runs produce the SAME id -> idempotent MERGE/upsert.
ID_NAMESPACE = uuid.UUID("5b8e7e2a-1f3c-4a6b-9d0e-7c2a4f6b8d1e")

# Keyword -> topic label, checked in order. First match wins.
TOPIC_KEYWORDS = [
    ("solar", ["solar"]),
    ("EV", ["electric vehicle", "electric car", " ev ", "ev,", "ev.", "e-car"]),
    ("nuclear", ["nuclear"]),
]


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


def transform_news(raw_articles: list[dict]) -> list[dict]:
    """Bronze raw articles -> conformed, scored, deduped Silver rows.

    - VADER sentiment on title + description
    - topic classification (solar / EV / nuclear / general)
    - deterministic id from the URL (stable across runs -> idempotent upsert)
    - dedupe by id (the same article re-fetched across Bronze files -> one row)
    """
    analyzer = SentimentIntensityAnalyzer()
    by_id: dict[str, dict] = {}

    for article in raw_articles:
        title = article.get("title") or ""
        description = article.get("description") or ""
        url = article.get("url") or ""

        text = f"{title}. {description}".strip()
        compound = analyzer.polarity_scores(text)["compound"]
        record_id = str(uuid.uuid5(ID_NAMESPACE, url or title))

        # Keyed by id, so a duplicate article overwrites itself -> dedup.
        by_id[record_id] = {
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

    rows = list(by_id.values())
    rows.sort(key=lambda r: r.get("published_at") or "")
    return rows
