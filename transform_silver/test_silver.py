"""Unit tests for the Silver transform — pure logic, no Azure, runs in <1s.

    python -m pytest transform_silver -q
"""

from silver import classify_topic, sentiment_label, transform_news


def test_sentiment_label_thresholds():
    assert sentiment_label(0.5) == "positive"
    assert sentiment_label(-0.5) == "negative"
    assert sentiment_label(0.0) == "neutral"


def test_classify_topic():
    assert classify_topic("a new solar farm opens") == "solar"
    assert classify_topic("nuclear reactor restarts") == "nuclear"
    assert classify_topic("electric vehicle sales rise") == "EV"
    assert classify_topic("an unrelated headline") == "general"


def test_transform_news_dedupes_same_url():
    # Same article appearing twice (e.g. re-fetched across two Bronze files).
    article = {
        "title": "Solar power soars",
        "description": "great wonderful record success",
        "url": "http://example.com/solar-1",
        "source": {"name": "EnergyDaily"},
        "publishedAt": "2026-06-01T00:00:00Z",
    }
    rows = transform_news([article, dict(article)])

    assert len(rows) == 1                       # deduped to one row
    assert rows[0]["topic"] == "solar"
    assert rows[0]["source"] == "EnergyDaily"
    assert rows[0]["sentiment_label"] == "positive"   # clearly positive text


def test_transform_news_deterministic_id():
    raw = [{
        "title": "EV market update",
        "description": "",
        "url": "http://example.com/ev",
        "source": {"name": "S"},
        "publishedAt": "2026-06-02T00:00:00Z",
    }]
    assert transform_news(raw)[0]["id"] == transform_news(raw)[0]["id"]


def test_transform_news_handles_empty():
    assert transform_news([]) == []
