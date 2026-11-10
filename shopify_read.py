"""W05-D2 - read ONE product by hand before writing anything. Read-only.

Run:  python shopify_read.py
"""

import json

from shopify_api import get_token, graphql

# A "query" only reads. GraphQL returns exactly the fields named here, nothing else.
# The fields are the ones W05-D3 will need to send when it creates a product.
QUERY = """
query OneProduct {
  products(first: 1) {
    nodes {
      id
      title
      handle
      status
      descriptionHtml
      productType
      vendor
      tags
      options { name values }
      variants(first: 5) {
        nodes { id title price sku selectedOptions { name value } }
      }
      media(first: 3) {
        nodes { ... on MediaImage { image { url } } }
      }
    }
  }
}
"""

token = get_token()
response = graphql(token, QUERY)

# Task 2: print the status code and the raw JSON, before interpreting anything.
print("status code:", response.status_code)
body = response.json()
print(json.dumps(body, indent=2, ensure_ascii=False))

# GraphQL can say 200 and still have failed - the errors are inside the body.
if body.get("errors"):
    raise SystemExit("\nHTTP 200, but the query had errors (see 'errors' above).")
