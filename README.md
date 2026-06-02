# azure-energy-sentiment-pipeline

GitHub Repo (push triggers CI)
↓
Terraform (provisions Azure infra)
↓
┌────────────────────────────────┐
│         Azure Resources        │
│  - Blob Storage (raw landing)  │
│  - Azure Data Factory          │
│  - Key Vault (secrets)         │
└────────────────────────────────┘
↓
Two Data Sources run on schedule:

```
[Source 1]              [Source 2]
News API                EPA CO2 API
fetch_news.py           fetch_co2.py
     ↓                       ↓
VADER sentiment         Clean + normalize
scoring                 CO2 readings
     ↓                       ↓
Blob Storage            Blob Storage
/raw/news/              /raw/co2/
          ↓           ↓
      Azure Data Factory
      (two pipelines)
          ↓
     Dataverse
┌─────────────────────────────────────┐
│  Table 1: climate_news              │
│  - id (guid)                        │
│  - title (text)                     │
│  - source (text)                    │
│  - topic (text: EV/solar/nuclear)   │
│  - sentiment_compound (float)       │
│  - sentiment_label (text)           │
│  - published_at (datetime)          │
│  - url (text)                       │
│                                     │
│  Table 2: co2_readings              │
│  - id (guid)                        │
│  - region (text)                    │
│  - co2_ppm (float)                  │
│  - recorded_at (datetime)           │
│  - source (text)                    │
└─────────────────────────────────────┘
          ↓
     Power Automate
(trigger: sentiment_compound < -0.3)
→ sends email alert with article title
          ↓
     Power BI Desktop
- Sentiment trend over time
- CO2 levels by region
- Correlation: negative news vs CO2 spikes
```


