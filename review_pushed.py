"""W06-D4 - read pushed bags back from Shopify and check each one against catalog.db.

The admin is where a PERSON reviews a batch (do the photos and words look right?).
This script checks the FACTS for every product, so nothing slips past a tired eye:
  - the product exists at the id we stored
  - it is a DRAFT, the vendor and title are ours
  - it has one variant, at price 0.00
  - it has as many photos as the bag has on disk, all READY (not FAILED / still processing)

Read-only: it never changes anything in Shopify or in catalog.db.

Run:  python review_pushed.py                    (every pushed bag)
      python review_pushed.py bag-003 bag-004    (just these)
"""

import argparse
import logging

from catalog import connect, get_product
from group_photos import group_photos
from log_setup import setup_logging
from shopify_api import check, get_token, graphql

log = logging.getLogger("review")

READ_BACK = """
query ReadBack($id: ID!) {
  product(id: $id) {
    id title status vendor
    variants(first: 5) { nodes { price } }
    media(first: 50) { nodes { status } }
  }
}
"""


def problems_with(product, row, photo_count):
    """Everything wrong with one product, as short sentences. An empty list means OK."""
    if product is None:
        return ["not found in Shopify (deleted, or the stored id is wrong)"]
    found = []
    if product["status"] != "DRAFT":
        found.append(f"status is {product['status']}, expected DRAFT")
    if product["title"] != row["title"]:
        found.append(f"title is {product['title']!r}, catalog has {row['title']!r}")
    if product["vendor"] != "Protshi Garments":
        found.append(f"vendor is {product['vendor']!r}")
    prices = [v["price"] for v in product["variants"]["nodes"]]
    if prices != ["0.00"]:
        found.append(f"variant prices are {prices}, expected one at 0.00")
    statuses = [m["status"] for m in product["media"]["nodes"]]
    if len(statuses) != photo_count:
        found.append(f"{len(statuses)} photos in Shopify, {photo_count} on disk")
    not_ready = [s for s in statuses if s != "READY"]
    if not_ready:
        found.append(f"photos not READY: {not_ready}")
    return found


def review(con, token, keys, photos):
    """Check each bag; return {group_key: [problems]} for the ones with problems."""
    bad = {}
    for key in keys:
        row = get_product(con, key)
        if row is None or not row["shopify_product_id"]:
            bad[key] = ["not pushed (no shopify_product_id in catalog.db)"]
            log.error("%s: not pushed", key)
            continue
        product = check(graphql(token, READ_BACK, {"id": row["shopify_product_id"]}))["product"]
        found = problems_with(product, row, len(photos.get(key, [])))
        if found:
            bad[key] = found
            log.error("%s: %s", key, "; ".join(found))
        else:
            log.info("%s: OK | DRAFT | 0.00 | %d photo%s READY | %s", key,
                     len(photos[key]), "s" if len(photos[key]) > 1 else "", product["title"])
    log.info("Reviewed %d: %d OK, %d with problems.", len(keys), len(keys) - len(bad), len(bad))
    return bad


def main():
    parser = argparse.ArgumentParser(description="Read pushed bags back from Shopify and check them.")
    parser.add_argument("groups", nargs="*", help="group keys (default: every pushed bag)")
    args = parser.parse_args()
    setup_logging()

    con = connect()
    keys = args.groups or [r["group_key"] for r in con.execute(
        "SELECT group_key FROM products WHERE shopify_product_id IS NOT NULL ORDER BY group_key")]
    bad = review(con, get_token(), keys, group_photos("photos"))
    con.close()
    if bad:
        raise SystemExit(1)       # a non-zero exit code, so a script can stop on it


if __name__ == "__main__":
    main()
