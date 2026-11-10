"""All talking to Shopify lives here: get a token, send a GraphQL request.

Uses the GraphQL Admin API, not REST (REST is legacy at Shopify - see NOTES.md, W05).
"""

import os

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


def graphql(token, query, variables=None):
    """Send one GraphQL request. Returns the raw requests.Response - check it yourself.

    GraphQL always uses POST, even to read: the query travels in the request body.
    """
    domain, _, _ = _settings()
    return requests.post(
        f"https://{domain}/admin/api/{API_VERSION}/graphql.json",
        json={"query": query, "variables": variables or {}},
        headers={"X-Shopify-Access-Token": token},
        timeout=TIMEOUT,
    )


def check(response):
    """Return the 'data' part, or raise. Two checks, because GraphQL can fail inside a 200."""
    if response.status_code != 200:
        raise ShopifyError(f"HTTP {response.status_code}: {response.text[:300]}")
    body = response.json()
    if body.get("errors"):
        raise ShopifyError(f"HTTP 200 but GraphQL errors: {body['errors']}")
    return body["data"]
