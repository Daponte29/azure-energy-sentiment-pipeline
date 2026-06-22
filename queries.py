"""Ad-hoc SQL over the pipeline JSON using DuckDB — stays in your IDE.

Two modes:
    python queries.py            # query the LOCAL files under data/ (fast, offline)
    python queries.py --blob     # query the LIVE files in Azure Blob Storage

--blob reads straight from the container via DuckDB's azure extension (no
download). It needs AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME in
your .env (the same vars the upload uses).

Edit QUERY below, then run one of the commands above.
"""

from __future__ import annotations

import sys

import duckdb

# DuckDB's table output uses Unicode box characters; force UTF-8 on Windows.
sys.stdout.reconfigure(encoding="utf-8")

USE_BLOB = "--blob" in sys.argv

con = duckdb.connect()

if USE_BLOB:
    import os

    from dotenv import load_dotenv

    load_dotenv()
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container = os.getenv("AZURE_CONTAINER_NAME")
    if not connection_string or not container:
        sys.exit(
            "--blob needs AZURE_STORAGE_CONNECTION_STRING and "
            "AZURE_CONTAINER_NAME set in your .env"
        )

    con.execute("INSTALL azure; LOAD azure;")
    # Single quotes can't appear in an Azure connection string, but double any
    # just in case so the inlined secret can't break the statement.
    safe_cs = connection_string.replace("'", "''")
    con.execute(f"CREATE OR REPLACE SECRET az (TYPE azure, CONNECTION_STRING '{safe_cs}')")
    base = f"azure://{container}"
    print(f"Querying LIVE blob: {base}/\n")
else:
    base = "data"
    print("Querying LOCAL files under data/\n")

NEWS = f"{base}/news/news_latest.json"
CO2 = f"{base}/co2/co2_latest.json"

# ---- edit this and re-run -------------------------------------------------
QUERY = f"""
SELECT topic,
       COUNT(*)                          AS articles,
       ROUND(AVG(sentiment_compound), 3) AS avg_sentiment,
       SUM(CASE WHEN sentiment_compound < -0.3 THEN 1 ELSE 0 END) AS alerts
FROM read_json_auto('{NEWS}')
GROUP BY topic
ORDER BY articles DESC
"""
# ---------------------------------------------------------------------------

# Other examples to paste into QUERY:
#   top emitting states:
#     SELECT state_name, ROUND(SUM(co2e_emission)) AS total
#     FROM read_json_auto('{CO2}') GROUP BY state_name ORDER BY total DESC LIMIT 10
#   emissions by sector:
#     SELECT sector, ROUND(SUM(co2e_emission)) AS total
#     FROM read_json_auto('{CO2}') GROUP BY sector ORDER BY total DESC
#   --blob only: scan EVERY file in a prefix, not just _latest:
#     FROM read_json_auto('azure://<container>/news/*.json')

con.sql(QUERY).show(max_rows=100)
