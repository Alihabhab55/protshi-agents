"""W05-D4 to D6 - push extracted bags to Shopify as drafts, with all their photos in order.

DRY RUN BY DEFAULT: prints what it would send and sends nothing. --confirm pushes for real.
Bags that already have a shopify_product_id are skipped - pushing twice creates nothing.

Run:  python push.py --limit 1              (dry run: show the next bag)
      python push.py --limit 1 --confirm    (create it in Shopify)
      python push.py bag-005 --confirm      (a specific bag)
"""

import argparse
import html
import json
import time

from catalog import connect, get_product, mark_pushed
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


def show_dry_run(row, photo_paths):
    """Print exactly what would be sent. Touches nothing: no token, no upload, no write."""
    print("  would create:")
    body = json.dumps(product_input(row), indent=2, ensure_ascii=False)
    print("    " + body.replace("\n", "\n    "))
    print(f"  would upload {len(photo_paths)} photo(s), in this order:")
    for n, path in enumerate(photo_paths, start=1):
        print(f"    {n}. {path}  ({media_type_of(path)})")


def bags_to_push(con, requested):
    """The rows to push: the bags named on the command line, or else every bag that
    is extracted and not yet in Shopify - sorted, so --limit 1 is always the same one."""
    if requested:
        return [(key, get_product(con, key)) for key in requested]
    keys = [r["group_key"] for r in con.execute(
        "SELECT group_key FROM products WHERE status = 'extracted' "
        "AND shopify_product_id IS NULL ORDER BY group_key")]
    return [(key, get_product(con, key)) for key in keys]


def main():
    parser = argparse.ArgumentParser(
        description="Push extracted bags to Shopify as drafts. DRY RUN unless --confirm.")
    parser.add_argument("groups", nargs="*", help="group keys (default: every bag not yet pushed)")
    parser.add_argument("--limit", type=int, default=None, help="push at most N bags")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="show what would be sent, send nothing (the default anyway)")
    mode.add_argument("--confirm", action="store_true",
                      help="really create the products in Shopify")
    args = parser.parse_args()
    live = args.confirm

    con = connect()
    photos = group_photos("photos")
    candidates = bags_to_push(con, args.groups)
    # Token only for a real push: a dry run must not talk to Shopify at all.
    token = get_token() if live else None

    print("LIVE PUSH - creating products in Shopify\n" if live
          else "DRY RUN - nothing will be sent. Add --confirm to push for real.\n")

    done = 0
    for group_key, row in candidates:
        if args.limit is not None and done >= args.limit:
            break
        # W05-D5: check the database first. A Shopify id means it's already there -
        # pushing again would create a duplicate product.
        if row and row["shopify_product_id"]:
            print(f"{group_key}: already pushed as {row['shopify_product_id']} - nothing to push")
            continue
        if row is None or row["status"] != "extracted":
            print(f"{group_key}: not extracted - skipped")
            continue

        print(f"{group_key}: {row['title']} ({len(photos[group_key])} photo{'s' if len(photos[group_key]) > 1 else ''})")
        if not live:
            show_dry_run(row, photos[group_key])
            done += 1
            continue

        if done > 0:
            time.sleep(PAUSE_SECONDS)
        product_id = push_bag(token, row, photos[group_key])
        # Save straight away. The gap between "Shopify created it" and "we wrote it
        # down" is the one moment a crash could still cause a duplicate - keep it tiny.
        mark_pushed(con, group_key, product_id)
        print(f"  saved: status=pushed, shopify_product_id={product_id}")
        done += 1

    if live:
        print(f"\n{done} pushed" if done else "\nNothing to push.")
    else:
        print(f"\nDry run: {done} bag(s) shown, 0 sent." if done else "\nNothing to push.")
    con.close()


if __name__ == "__main__":
    main()
