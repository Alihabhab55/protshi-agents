"""W04-D2 - the catalog database. All SQL for this project lives in this file.

Run:  python catalog.py   (creates catalog.db and the products table, then lists the columns)
"""

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
    group_key           TEXT    NOT NULL,          -- "bag-002"
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
    shopify_product_id  INTEGER                    -- filled in week 5
)
"""


def connect(path=DB_PATH):
    """Open the database and make sure the tables exist."""
    con = sqlite3.connect(path)
    con.execute(CREATE_PRODUCTS)
    con.commit()
    return con


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
