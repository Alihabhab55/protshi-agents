"""All talking to Shopify lives here: get a token, send a GraphQL request.

Uses the GraphQL Admin API, not REST (REST is legacy at Shopify - see NOTES.md, W05).
"""

import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

API_VERSION = "2026-10"   # pinned: Shopify releases a new version every 3 months
TIMEOUT = 30              # seconds; never wait forever on the network


class ShopifyError(Exception):
    """Shopify answered, but not with what we asked for."""


def _settings():
    load_dotenv()
    names = ["SHOPIFY_STORE_DOMAIN", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET"]
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
    return [os.getenv(n) for n in names]


def get_token():
    """Trade the app's client ID + secret for an access token valid 24 hours.

    The client credentials grant (W05-D1). The token is kept in memory only.
    """
    domain, client_id, client_secret = _settings()
    response = requests.post(
        f"https://{domain}/admin/oauth/access_token",
        data={"grant_type": "client_credentials",
              "client_id": client_id, "client_secret": client_secret},
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        raise ShopifyError(f"token request failed: HTTP {response.status_code} "
                           f"{response.text[:200]}")
    return response.json()["access_token"]


MAX_ATTEMPTS = 4


def _throttled(response):
    """Shopify says "slow down" two ways: HTTP 429, or a 200 whose errors say THROTTLED."""
    if response.status_code == 429:
        return True
    if response.status_code == 200:
        errors = response.json().get("errors") or []
        return any(e.get("extensions", {}).get("code") == "THROTTLED" for e in errors)
    return False


def graphql(token, query, variables=None):
    """Send one GraphQL request. Returns the raw requests.Response - check it yourself.

    GraphQL always uses POST, even to read: the query travels in the request body.
    W05-D4: when Shopify says "too many requests", wait and try again (up to 4 times).
    """
    domain, _, _ = _settings()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.post(
            f"https://{domain}/admin/api/{API_VERSION}/graphql.json",
            json={"query": query, "variables": variables or {}},
            headers={"X-Shopify-Access-Token": token},
            timeout=TIMEOUT,
        )
        if not _throttled(response) or attempt == MAX_ATTEMPTS:
            return response
        # Retry-After = how many seconds Shopify asks us to wait. Otherwise back off:
        # 2, 4, 8 seconds - waiting longer each time gives the bucket time to refill.
        wait = float(response.headers.get("Retry-After", 2 ** attempt))
        print(f"  Shopify says slow down (attempt {attempt}) - waiting {wait:.0f}s")
        time.sleep(wait)


def check(response):
    """Return the 'data' part, or raise. Two checks, because GraphQL can fail inside a 200."""
    if response.status_code != 200:
        raise ShopifyError(f"HTTP {response.status_code}: {response.text[:300]}")
    body = response.json()
    if body.get("errors"):
        raise ShopifyError(f"HTTP 200 but GraphQL errors: {body['errors']}")
    return body["data"]


STAGE = """
mutation Stage($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""


def upload_image(token, path, media_type):
    """Upload one local photo to Shopify's storage. Returns its resourceUrl.

    Step 1: ask for an upload slot. Step 2: PUT the file's bytes into it.
    The photo is not on any product yet - productCreate(media=...) attaches it.
    """
    path = Path(path)
    data = check(graphql(token, STAGE, {"input": [{
        "resource": "IMAGE",
        "filename": path.name,
        "mimeType": media_type,
        "httpMethod": "PUT",
    }]}))["stagedUploadsCreate"]
    if data["userErrors"]:
        raise ShopifyError(f"upload slot refused for {path.name}: {data['userErrors']}")

    target = data["stagedTargets"][0]
    # For PUT uploads the "parameters" are headers to send along (content type, etc.).
    headers = {p["name"]: p["value"] for p in target["parameters"]}
    put = requests.put(target["url"], data=path.read_bytes(), headers=headers, timeout=120)
    if put.status_code not in (200, 201):
        raise ShopifyError(f"upload of {path.name} failed: HTTP {put.status_code} {put.text[:200]}")
    return target["resourceUrl"]
