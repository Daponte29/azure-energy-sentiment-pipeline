"""Create the Dataverse tables for the Energy News Sentiment Pipeline via the
Web API (bypasses the maker UI).

Creates, in order and idempotently:
    1. Publisher  "Climate Pipeline"      (customization prefix: cp)
    2. Solution   "Energy News Pipeline"
    3. Table      cp_climatenews    (Table 1: news + VADER sentiment)
    4. Table      cp_co2emission    (Table 2: EPA emissions, state x sector x year)

Auth: reuses your Azure CLI login. The script asks `az` for a token scoped to
the Dataverse environment (no client secret needed). Set DATAVERSE_TOKEN to
override, or DATAVERSE_URL to target a different environment.
"""

from __future__ import annotations

import os
import subprocess
import sys

import requests

DATAVERSE_URL = os.getenv(
    "DATAVERSE_URL", "https://org08456745.crm.dynamics.com"
).rstrip("/")
API = f"{DATAVERSE_URL}/api/data/v9.2"
LCID = 1033  # English

PUBLISHER_UNIQUE = "climatepipeline"
PUBLISHER_PREFIX = "cp"
PUBLISHER_OPTION_VALUE_PREFIX = 65111
SOLUTION_UNIQUE = "energynewspipeline"

# az.cmd is not always on PATH; fall back to the standard install location.
AZ_FALLBACK = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"


# --------------------------------------------------------------------------- #
# Auth + HTTP helpers
# --------------------------------------------------------------------------- #
def get_token() -> str:
    token = os.getenv("DATAVERSE_TOKEN")
    if token:
        return token

    for az in ("az", AZ_FALLBACK):
        try:
            result = subprocess.run(
                [
                    az,
                    "account",
                    "get-access-token",
                    "--resource",
                    DATAVERSE_URL,
                    "--query",
                    "accessToken",
                    "-o",
                    "tsv",
                ],
                capture_output=True,
                text=True,
                shell=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            continue
    sys.exit("Could not obtain a token. Run 'az login' or set DATAVERSE_TOKEN.")


def headers(token: str, solution: str | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    if solution:
        h["MSCRM.SolutionUniqueName"] = solution
    return h


# --------------------------------------------------------------------------- #
# Metadata builders
# --------------------------------------------------------------------------- #
def label(text: str) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text,
                "LanguageCode": LCID,
            }
        ],
    }


def string_attr(
    schema, display, max_length=200, fmt="Text", primary=False, required="None"
) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
        "AttributeType": "String",
        "AttributeTypeName": {"Value": "StringType"},
        "SchemaName": schema,
        "DisplayName": label(display),
        "RequiredLevel": {"Value": required},
        "MaxLength": max_length,
        "FormatName": {"Value": fmt},
        "IsPrimaryName": primary,
    }


def decimal_attr(schema, display, precision, min_value, max_value) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
        "AttributeType": "Decimal",
        "AttributeTypeName": {"Value": "DecimalType"},
        "SchemaName": schema,
        "DisplayName": label(display),
        "RequiredLevel": {"Value": "None"},
        "Precision": precision,
        "MinValue": min_value,
        "MaxValue": max_value,
    }


def int_attr(schema, display, min_value=0, max_value=2147483647) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
        "AttributeType": "Integer",
        "AttributeTypeName": {"Value": "IntegerType"},
        "SchemaName": schema,
        "DisplayName": label(display),
        "RequiredLevel": {"Value": "None"},
        "MinValue": min_value,
        "MaxValue": max_value,
    }


def datetime_attr(schema, display) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
        "AttributeType": "DateTime",
        "AttributeTypeName": {"Value": "DateTimeType"},
        "SchemaName": schema,
        "DisplayName": label(display),
        "RequiredLevel": {"Value": "None"},
        "Format": "DateAndTime",
        "DateTimeBehavior": {"Value": "TimeZoneIndependent"},
    }


def entity_def(
    schema, display, plural, description, primary_logical, attributes
) -> dict:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": schema,
        "DisplayName": label(display),
        "DisplayCollectionName": label(plural),
        "Description": label(description),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasActivities": False,
        "HasNotes": False,
        "PrimaryNameAttribute": primary_logical,
        "Attributes": attributes,
    }


# --------------------------------------------------------------------------- #
# Create operations (idempotent)
# --------------------------------------------------------------------------- #
def ensure_publisher(token: str) -> None:
    r = requests.get(
        f"{API}/publishers?$filter=uniquename eq '{PUBLISHER_UNIQUE}'&$select=publisherid",
        headers=headers(token),
        timeout=60,
    )
    r.raise_for_status()
    if r.json().get("value"):
        print(f"Publisher '{PUBLISHER_UNIQUE}' already exists — skipping.")
        return

    body = {
        "uniquename": PUBLISHER_UNIQUE,
        "friendlyname": "Climate Pipeline",
        "customizationprefix": PUBLISHER_PREFIX,
        "customizationoptionvalueprefix": PUBLISHER_OPTION_VALUE_PREFIX,
    }
    resp = requests.post(
        f"{API}/publishers", headers=headers(token), json=body, timeout=60
    )
    resp.raise_for_status()
    print(f"Created publisher '{PUBLISHER_UNIQUE}' (prefix '{PUBLISHER_PREFIX}').")


def ensure_solution(token: str) -> None:
    r = requests.get(
        f"{API}/solutions?$filter=uniquename eq '{SOLUTION_UNIQUE}'&$select=solutionid",
        headers=headers(token),
        timeout=60,
    )
    r.raise_for_status()
    if r.json().get("value"):
        print(f"Solution '{SOLUTION_UNIQUE}' already exists — skipping.")
        return

    pub = requests.get(
        f"{API}/publishers?$filter=uniquename eq '{PUBLISHER_UNIQUE}'&$select=publisherid",
        headers=headers(token),
        timeout=60,
    ).json()["value"][0]

    body = {
        "uniquename": SOLUTION_UNIQUE,
        "friendlyname": "Energy News Pipeline",
        "version": "1.0.0.0",
        "publisherid@odata.bind": f"/publishers({pub['publisherid']})",
    }
    resp = requests.post(
        f"{API}/solutions", headers=headers(token), json=body, timeout=60
    )
    resp.raise_for_status()
    print(f"Created solution '{SOLUTION_UNIQUE}'.")


def ensure_table(token: str, logical_name: str, definition: dict) -> None:
    check = requests.get(
        f"{API}/EntityDefinitions(LogicalName='{logical_name}')?$select=LogicalName",
        headers=headers(token),
        timeout=60,
    )
    if check.status_code == 200:
        print(f"Table '{logical_name}' already exists — skipping.")
        return

    resp = requests.post(
        f"{API}/EntityDefinitions",
        headers=headers(token, solution=SOLUTION_UNIQUE),
        json=definition,
        timeout=120,
    )
    if not resp.ok:
        print(f"FAILED to create '{logical_name}': {resp.status_code}")
        print(resp.text)
        resp.raise_for_status()
    print(f"Created table '{logical_name}'.")


# --------------------------------------------------------------------------- #
# Table definitions
# --------------------------------------------------------------------------- #
def climate_news_def() -> dict:
    attrs = [
        string_attr("cp_Title", "Title", max_length=400, primary=True),
        string_attr("cp_Source", "Source", max_length=200),
        string_attr("cp_Topic", "Topic", max_length=50),
        decimal_attr("cp_SentimentCompound", "Sentiment Compound", 4, -1, 1),
        string_attr("cp_SentimentLabel", "Sentiment Label", max_length=20),
        datetime_attr("cp_PublishedAt", "Published At"),
        string_attr("cp_Url", "URL", max_length=500, fmt="Url"),
    ]
    return entity_def(
        "cp_ClimateNews",
        "Climate News",
        "Climate News",
        "Energy news articles scored with VADER sentiment.",
        "cp_title",
        attrs,
    )


def co2_emission_def() -> dict:
    attrs = [
        string_attr("cp_Name", "Name", max_length=200, primary=True),
        string_attr("cp_State", "State", max_length=10),
        string_attr("cp_StateName", "State Name", max_length=100),
        string_attr("cp_Sector", "Sector", max_length=100),
        decimal_attr("cp_Co2eEmission", "CO2e Emission", 3, 0, 100000000000),
        string_attr("cp_EmissionUnit", "Emission Unit", max_length=50),
        int_attr("cp_FacilityCount", "Facility Count"),
        int_attr("cp_Year", "Year", min_value=1900, max_value=2200),
        datetime_attr("cp_RecordedAt", "Recorded At"),
        string_attr("cp_Source", "Source", max_length=100),
    ]
    return entity_def(
        "cp_Co2Emission",
        "CO2 Emission",
        "CO2 Emissions",
        "EPA GHG emissions aggregated by state, sector, and year (CO2e).",
        "cp_name",
        attrs,
    )


def main() -> None:
    print(f"Target environment: {DATAVERSE_URL}")
    token = get_token()

    ensure_publisher(token)
    ensure_solution(token)
    ensure_table(token, "cp_climatenews", climate_news_def())
    ensure_table(token, "cp_co2emission", co2_emission_def())
    print("Done.")


if __name__ == "__main__":
    main()
