"""W05-D3 - create ONE hardcoded draft product, then go and look at it in Shopify admin.

Every run creates a NEW product (no duplicate check yet - that's W05-D5).
Run once:  python shopify_create_one.py
"""

import json

from shopify_api import check, get_token, graphql

# A "mutation" writes. $product is a variable: the values travel separately from the
# query text, like the :title placeholders in catalog.py - never pasted into it.
CREATE = """
mutation CreateDraft($product: ProductCreateInput!) {
  productCreate(product: $product) {
    product {
      id
      title
      status
      handle
      variants(first: 1) { nodes { id price } }
    }
    userErrors { field message }
  }
}
"""

TEST_PRODUCT = {
    "title": "TEST - Protshi agent draft - delete me",
    "descriptionHtml": "<p>A test product created by the Protshi agent (W05-D3). "
                       "Safe to delete.</p>",
    "productType": "tote",
    "vendor": "Protshi Garments",
    "tags": ["protshi-agent-test"],
    "status": "DRAFT",     # never ACTIVE: a person reviews every listing first
}

token = get_token()
response = graphql(token, CREATE, {"product": TEST_PRODUCT})

print("status code:", response.status_code)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

data = check(response)    # layers 1 and 2: HTTP 200, and no GraphQL "errors"

# Layer 3, for mutations only: the request was fine, but Shopify refused the CHANGE
# (e.g. a title too long). That comes back as userErrors - inside a 200, no "errors".
result = data["productCreate"]
if result["userErrors"]:
    raise SystemExit(f"\nShopify refused the product: {result['userErrors']}")

product = result["product"]
variant = product["variants"]["nodes"][0]
print(f"\nCreated {product['id']}")
print(f"  status {product['status']}, 1 variant at price {variant['price']}")
assert product["status"] == "DRAFT" and variant["price"] == "0.00"
