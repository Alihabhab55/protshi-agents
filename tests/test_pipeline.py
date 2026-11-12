"""W06-D3 - four promises the pipeline makes, each checked without any API, network or catalog.db.

Run:  pytest
"""

import os

import pytest
from pydantic import ValidationError

from extract import decide
from fakes import ELEVEN_TAGS, GOOD
from group_photos import group_photos
from push import product_input
from schema import ProductDraft


def test_schema_rejects_eleven_tags():
    ProductDraft(**GOOD)                    # the base record is valid: only the tags differ below
    with pytest.raises(ValidationError) as caught:
        ProductDraft(**ELEVEN_TAGS)
    assert caught.value.errors()[0]["loc"] == ("tags",)
    ten = {**GOOD, "tags": [f"tag{i}" for i in range(10)]}
    assert len(ProductDraft(**ten).tags) == 10      # the limit is 10, not 9


def test_grouper_turns_two_photos_into_one_product(tmp_path):
    # Photos _2 and _10 on purpose: as text, "_10" sorts before "_2", and so does the file
    # system. The grouper must order by photo NUMBER, or the main photo ends up second.
    (tmp_path / "bag-014_10.jpg").write_bytes(b"")
    (tmp_path / "bag-014_2.jpg").write_bytes(b"")
    (tmp_path / "IMG_2417.jpeg").write_bytes(b"")   # not named by the convention: ignored
    groups = group_photos(tmp_path)
    assert list(groups) == ["bag-014"]
    assert [os.path.basename(p) for p in groups["bag-014"]] == ["bag-014_2.jpg", "bag-014_10.jpg"]


def test_push_payload_is_always_a_draft_at_zero():
    # Whatever the row says, the product Shopify receives is a DRAFT a person must review.
    for status in ("extracted", "pushed", "failed"):
        payload = product_input({**GOOD, "status": status, "shopify_product_id": None})
        assert payload["status"] == "DRAFT"
        # Shopify's ProductCreateInput has no price: it creates the one initial variant at
        # 0.00 (read back and confirmed in W05-D3/D4). Setting a price needs a different
        # mutation, so the promise we can test is "no price and no variants are ever sent".
        assert "variants" not in payload
        assert not any("price" in key.lower() for key in payload)


def test_decide_sends_only_what_the_database_does_not_have():
    # The one rule behind "skip or send to the model", shared by the dry run and the real run.
    h = "hash-of-the-photos"
    assert decide(None, h) == (True, "new")
    assert decide({"status": "extracted", "photo_hash": h}, h) == (False, "already extracted")
    assert decide({"status": "pushed", "photo_hash": h}, h) == (False, "already pushed")
    assert decide({"status": "extracted", "photo_hash": "older"}, h) == (True, "photos changed")
    assert decide({"status": "failed", "photo_hash": h}, h) == (True, "was failed")
    assert decide({"status": "pending", "photo_hash": None}, h) == (True, "was pending")
