"""W04-D2/D3 - the catalog database. All SQL for this project lives in this file.

Run:  python catalog.py   (creates catalog.db and the products table, then lists the columns)
"""

import json
import sqlite3

DB_PATH = "catalog.db"

# One row per bag group. Three kinds of columns:
#   identity     - which bag this is
#   content      - the nine ProductDraft fields (empty until extracted)
#   bookkeeping  - what happened to it, what it cost, where it went
CREATE_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    -- identity
    id                  INTEGER PRIMARY KEY,
    group_key           TEXT    NOT NULL UNIQUE,   -- "bag-002", at most one row per bag
    photo_hash          TEXT,                      -- fingerprint of the group's photos

    -- content: the nine ProductDraft fields
    title               TEXT,
    product_type        TEXT,
    colours             TEXT,                      -- JSON list as text: '["taupe", "tan"]'
    material            TEXT,
    size                TEXT,
    closure             TEXT,
    description         TEXT,
    seo_description     TEXT,
    tags                TEXT,                      -- JSON list as text

    -- bookkeeping
    status              TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'extracted', 'failed', 'pushed')),
    model_used          TEXT,                      -- "claude-opus-5"
    cost_usd            REAL,                      -- 0.0231
    error               TEXT,                      -- why it failed, if it did
    created_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    shopify_product_id  TEXT                       -- "gid://shopify/Product/..." (W05-D5)
)
"""


CONTENT_FIELDS = [
    "title", "product_type", "colours", "material", "size",
    "closure", "description", "seo_description", "tags",
]
LIST_FIELDS = {"colours", "tags"}   # stored as JSON text, read back as lists

# W04-D3: one statement that inserts a new bag OR updates the existing one.
# :name placeholders are filled in by sqlite3 from a dict - never by pasting
# values into the SQL string (a description like "women's tote" would break it).
# "excluded" means "the row we just tried to insert".
UPSERT_PRODUCT = f"""
INSERT INTO products (group_key, photo_hash, {", ".join(CONTENT_FIELDS)},
                      status, model_used, cost_usd, error)
VALUES (:group_key, :photo_hash, {", ".join(":" + f for f in CONTENT_FIELDS)},
        :status, :model_used, :cost_usd, :error)
ON CONFLICT (group_key) DO UPDATE SET
    photo_hash = excluded.photo_hash,
    {", ".join(f"{f} = excluded.{f}" for f in CONTENT_FIELDS)},
    status     = excluded.status,
    model_used = excluded.model_used,
    cost_usd   = excluded.cost_usd,
    error      = excluded.error,
    updated_at = CURRENT_TIMESTAMP
"""
# Not in the SET list on purpose: id and created_at (when the bag first appeared)
# and shopify_product_id (an update must never forget where the bag was pushed).


def _migrate_shopify_id_to_text(con):
    """W05-D5 migration: shopify_product_id INTEGER -> TEXT, keeping every row.

    SQLite can't change a column's type in place, so: build a new table with the
    right types, copy every row across, drop the old one, rename the new one.
    All inside one transaction - if any step fails, nothing has changed.
    """
    types = {row[1]: row[2] for row in con.execute("PRAGMA table_info(products)")}
    if types.get("shopify_product_id") != "INTEGER":
        return                              # already TEXT (or a fresh table): nothing to do

    con.execute("BEGIN")
    try:
        con.execute(CREATE_PRODUCTS.replace("CREATE TABLE IF NOT EXISTS products",
                                            "CREATE TABLE products_new"))
        con.execute("INSERT INTO products_new SELECT * FROM products")
        con.execute("DROP TABLE products")
        con.execute("ALTER TABLE products_new RENAME TO products")
        con.commit()
    except Exception:
        con.rollback()
        raise
    print("catalog.db: migrated shopify_product_id to TEXT")


def connect(path=DB_PATH):
    """Open the database and make sure the tables exist (and are up to date)."""
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row      # rows can be read by column name: row["title"]
    con.execute(CREATE_PRODUCTS)
    con.commit()
    _migrate_shopify_id_to_text(con)
    return con


def save_product(con, group_key, status, draft=None, *, photo_hash=None,
                 model_used=None, cost_usd=None, error=None):
    """Insert or update one bag. draft is a ProductDraft, or None for a failed bag."""
    values = {field: None for field in CONTENT_FIELDS}
    if draft is not None:
        # mode="json" turns enums into plain strings ("taupe"), like model_dump_json.
        values = draft.model_dump(mode="json")
        for field in LIST_FIELDS:
            values[field] = json.dumps(values[field])

    values.update(group_key=group_key, status=status, photo_hash=photo_hash,
                  model_used=model_used, cost_usd=cost_usd, error=error)
    con.execute(UPSERT_PRODUCT, values)
    con.commit()


def mark_pushed(con, group_key, shopify_product_id):
    """W05-D5: remember where this bag went. Committed at once, like save_product."""
    con.execute(
        "UPDATE products SET status = 'pushed', shopify_product_id = ?, "
        "updated_at = CURRENT_TIMESTAMP WHERE group_key = ?",
        (shopify_product_id, group_key),
    )
    con.commit()


def add_pending(con, group_key):
    """W06-D1: the ingest stage registers a bag the moment its photos land in photos/.

    INSERT OR IGNORE: group_key is UNIQUE, so if the row already exists nothing
    happens - running ingest twice never resets a bag that was extracted or pushed.
    Returns True if a new row was created.
    """
    cur = con.execute(
        "INSERT OR IGNORE INTO products (group_key, status) VALUES (?, 'pending')",
        (group_key,),
    )
    con.commit()
    return cur.rowcount == 1


def count_by_status(con):
    """{'extracted': 24, 'pushed': 2} - where every bag stands, in one line."""
    return {status: n for status, n in con.execute(
        "SELECT status, COUNT(*) FROM products GROUP BY status ORDER BY status")}


def get_product(con, group_key):
    """One bag as a dict (lists already turned back into lists), or None."""
    row = con.execute("SELECT * FROM products WHERE group_key = ?", (group_key,)).fetchone()
    if row is None:
        return None
    product = dict(row)
    for field in LIST_FIELDS:
        if product[field] is not None:
            product[field] = json.loads(product[field])
    return product


if __name__ == "__main__":
    con = connect()
    print(f"{DB_PATH} - products table:\n")
    # PRAGMA table_info asks SQLite to describe a table: one row per column.
    for _, name, col_type, not_null, default, _ in con.execute("PRAGMA table_info(products)"):
        extras = []
        if not_null:
            extras.append("NOT NULL")
        if default is not None:
            extras.append(f"DEFAULT {default}")
        print(f"  {name:<20} {col_type:<8} {' '.join(extras)}")
    con.close()
