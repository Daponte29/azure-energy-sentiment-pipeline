"""Register ADF's managed identity as a Dataverse application user and assign a
security role — via the Web API, because managed identities don't reliably show
up in the admin center's "Add an app" picker.

Idempotent: skips creation if the app user already exists.

Auth: reuses the Azure CLI login (same token approach as create_tables.py).
"""

from __future__ import annotations

import sys

import requests

from create_tables import API, get_token, headers

# Application (client) ID to register as a Dataverse app user. Pass one on the
# command line; defaults to the ADF service principal used by the copy pipelines.
DEFAULT_APP_ID = "1ade0e87-e413-47f8-8514-9770f1525ed1"  # adf-dataverse-sp
ADF_APP_ID = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_APP_ID
SECURITY_ROLE = "System Administrator"


def get_root_business_unit(token: str) -> str:
    r = requests.get(
        f"{API}/businessunits?$select=businessunitid&"
        f"$filter=_parentbusinessunitid_value eq null",
        headers=headers(token), timeout=60,
    )
    r.raise_for_status()
    return r.json()["value"][0]["businessunitid"]


def get_existing_app_user(token: str) -> str | None:
    r = requests.get(
        f"{API}/systemusers?$select=systemuserid,fullname&"
        f"$filter=applicationid eq {ADF_APP_ID}",
        headers=headers(token), timeout=60,
    )
    r.raise_for_status()
    rows = r.json().get("value")
    return rows[0]["systemuserid"] if rows else None


def create_app_user(token: str, business_unit_id: str) -> str:
    body = {
        "applicationid": ADF_APP_ID,
        "businessunitid@odata.bind": f"/businessunits({business_unit_id})",
    }
    resp = requests.post(f"{API}/systemusers", headers=headers(token), json=body, timeout=60)
    if not resp.ok:
        print("FAILED to create app user:", resp.status_code, resp.text)
        resp.raise_for_status()
    # OData-EntityId looks like .../systemusers(<guid>)
    entity_id = resp.headers["OData-EntityId"]
    user_id = entity_id.split("(")[1].rstrip(")")
    print(f"Created application user {user_id} for app {ADF_APP_ID}.")
    return user_id


def get_role_id(token: str, business_unit_id: str) -> str:
    r = requests.get(
        f"{API}/roles?$select=roleid,name&"
        f"$filter=name eq '{SECURITY_ROLE}' and _businessunitid_value eq {business_unit_id}",
        headers=headers(token), timeout=60,
    )
    r.raise_for_status()
    rows = r.json().get("value")
    if not rows:
        raise RuntimeError(f"Security role '{SECURITY_ROLE}' not found in root business unit.")
    return rows[0]["roleid"]


def assign_role(token: str, user_id: str, role_id: str) -> None:
    body = {"@odata.id": f"{API}/roles({role_id})"}
    resp = requests.post(
        f"{API}/systemusers({user_id})/systemuserroles_association/$ref",
        headers=headers(token), json=body, timeout=60,
    )
    if resp.status_code in (204, 200):
        print(f"Assigned role '{SECURITY_ROLE}'.")
    elif resp.status_code == 412 or "duplicate" in resp.text.lower():
        print(f"Role '{SECURITY_ROLE}' already assigned.")
    else:
        print("FAILED to assign role:", resp.status_code, resp.text)
        resp.raise_for_status()


def main() -> None:
    token = get_token()
    bu_id = get_root_business_unit(token)
    print(f"Root business unit: {bu_id}")

    user_id = get_existing_app_user(token)
    if user_id:
        print(f"App user already exists: {user_id} — skipping create.")
    else:
        user_id = create_app_user(token, bu_id)

    role_id = get_role_id(token, bu_id)
    assign_role(token, user_id, role_id)
    print("Done.")


if __name__ == "__main__":
    main()
