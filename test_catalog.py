"""W04-D3 - write the same group twice, confirm there is still one row.

Uses an in-memory database, so catalog.db is never touched.
Run:  python test_catalog.py
"""

import sqlite3

from catalog import connect, get_product, save_product
from schema import ProductDraft

con = connect(":memory:")

first = ProductDraft(
    title="Chevron Quilted Small Top-Handle Tote",
    product_type="tote", colours=["black"], material="leather-look", size="small",
    closure="zip", description="A women's quilted tote.",   # apostrophe on purpose
    seo_description="Black quilted tote.", tags=["tote", "quilted"],
)
# model_validate, not model_copy(update=...): model_copy skips validation,
# so "mini" would stay a plain string instead of becoming Size.mini.
second = ProductDraft.model_validate(
    {**first.model_dump(), "title": "Braided Quilt Mini Tote", "size": "mini"}
)

save_product(con, "bag-014", "extracted", first, cost_usd=0.023, model_used="claude-opus-5")
row_1 = get_product(con, "bag-014")
print("after write 1:", row_1["id"], row_1["title"], row_1["size"], row_1["colours"])

# Pretend week 5 pushed it, so we can prove the update leaves this alone.
con.execute("UPDATE products SET shopify_product_id = 777 WHERE group_key = 'bag-014'")
con.commit()

save_product(con, "bag-014", "extracted", second, cost_usd=0.025, model_used="claude-opus-5")
row_2 = get_product(con, "bag-014")
print("after write 2:", row_2["id"], row_2["title"], row_2["size"], row_2["colours"])

count = con.execute("SELECT COUNT(*) FROM products WHERE group_key = 'bag-014'").fetchone()[0]
print("rows for bag-014:", count)

assert count == 1                                    # still one row
assert row_2["title"] == "Braided Quilt Mini Tote"   # the second write's values won
assert row_2["size"] == "mini" and row_2["cost_usd"] == 0.025
assert row_2["id"] == row_1["id"]                    # same row, updated in place
assert row_2["created_at"] == row_1["created_at"]    # birth date kept
assert row_2["shopify_product_id"] == 777            # never forgotten by an update
assert row_2["colours"] == ["black"]                 # JSON text came back as a list
assert row_2["description"] == "A women's quilted tote."

# A failed bag still gets a row - with the reason, and no content.
save_product(con, "bag-015", "failed", error="tags: at most 10 items")
failed = get_product(con, "bag-015")
assert failed["status"] == "failed" and failed["title"] is None

# UNIQUE itself: a plain INSERT of an existing key is refused by the database.
try:
    con.execute("INSERT INTO products (group_key) VALUES ('bag-014')")
    raise AssertionError("duplicate was accepted")
except sqlite3.IntegrityError as e:
    print("plain INSERT of bag-014 again ->", e)

print("\nAll catalog checks passed.")
