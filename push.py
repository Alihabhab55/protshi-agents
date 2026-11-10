"""W05-D4 - push one extracted bag to Shopify as a draft, with all its photos in order.

Every run creates a NEW product - no duplicate check yet (that's W05-D5).
Run:  python push.py bag-002
"""

import argparse
import html
import time

from catalog import connect, get_product
from group_photos import group_photos
from images import media_type_of
from shopify_api import check, get_token, graphql, upload_image

PAUSE_SECONDS = 1.0     # between products, so a bulk push never hammers the API
WAIT_FOR_MEDIA = 30     # seconds to wait for Shopify to finish processing the photos

CREATE = """
mutation CreateDraft($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
  productCreate(product: $product, media: $media) {
    product { id title status variants(first: 1) { nodes { price } } }
    userErrors { field message }
  }
}
"""

MEDIA_STATUS = """
query Media($id: ID!) {
  product(id: $id) {
    media(first: 50) { nodes { status alt ... on MediaImage { image { url } } } }
  }
}
"""


def to_html(text):
    """Plain text -> Shopify's descriptionHtml. escape() so a '<' or '&' can't break it."""
    return f"<p>{html.escape(text)}</p>"


def product_input(row):
    """Map one catalog.db row to Shopify's ProductCreateInput (see NOTES.md, W05-D2)."""
    return {
        "title": row["title"],
        "descriptionHtml": to_html(row["description"]),
        "productType": row["product_type"],
        "vendor": "Protshi Garments",
        "tags": row["tags"],
        "status": "DRAFT",                        # always: a person reviews first
        "seo": {"title": row["title"], "description": row["seo_description"]},
    }


def push_bag(token, row, photo_paths):
    """Upload the photos, create the draft, wait for the photos. Returns the product id."""
    media = []
    for n, path in enumerate(photo_paths, start=1):
        media_type = media_type_of(path)          # from the bytes - lesson of W04-D6
        resource_url = upload_image(token, path, media_type)
        print(f"  uploaded {n}/{len(photo_paths)}: {path}")
        media.append({
            "originalSource": resource_url,
            "mediaContentType": "IMAGE",
            "alt": row["title"],                  # alt text: read aloud by screen readers
        })

    # The media list's order becomes the photo order on the product: _1 first.
    data = check(graphql(token, CREATE, {"product": product_input(row), "media": media}))
    result = data["productCreate"]
    if result["userErrors"]:
        raise SystemExit(f"Shopify refused the product: {result['userErrors']}")
    product = result["product"]
    print(f"  created {product['id']} - {product['status']}, "
          f"price {product['variants']['nodes'][0]['price']}")

    # Shopify processes photos after the product exists (status UPLOADED -> PROCESSING
    # -> READY). Wait a little so we can report what happened instead of guessing.
    deadline = time.monotonic() + WAIT_FOR_MEDIA
    while True:
        nodes = check(graphql(token, MEDIA_STATUS, {"id": product["id"]}))["product"]["media"]["nodes"]
        statuses = [m["status"] for m in nodes]
        if all(s in ("READY", "FAILED") for s in statuses) or time.monotonic() > deadline:
            break
        time.sleep(2)
    print(f"  photos: {len(nodes)} attached, statuses {statuses}")
    return product["id"]


def main():
    parser = argparse.ArgumentParser(description="Push extracted bags to Shopify as drafts.")
    parser.add_argument("groups", nargs="+", help="group keys, e.g. bag-002")
    args = parser.parse_args()

    con = connect()
    photos = group_photos("photos")
    token = get_token()

    for i, group_key in enumerate(args.groups):
        row = get_product(con, group_key)
        if row is None or row["status"] != "extracted":
            print(f"{group_key}: not extracted - skipped")
            continue
        if i > 0:
            time.sleep(PAUSE_SECONDS)
        print(f"{group_key}: {row['title']} ({len(photos[group_key])} photos)")
        push_bag(token, row, photos[group_key])
    con.close()


if __name__ == "__main__":
    main()
