"""W03-D2 - ProductDraft: the rules a bag record must pass before it goes anywhere.

Run:  python schema.py   (tries one good record and a few bad ones)
"""

from enum import Enum

from pydantic import BaseModel, Field


class Colour(str, Enum):
    """The colours customers can filter by. Anything else is rejected."""

    black = "black"
    white = "white"
    cream = "cream"
    beige = "beige"
    taupe = "taupe"
    tan = "tan"
    navy = "navy"
    red = "red"
    khaki = "khaki"
    silver = "silver"
    gold = "gold"
    brown = "brown"
    grey = "grey"
    burgundy = "burgundy"
    pink = "pink"
    green = "green"
    blue = "blue"


class Size(str, Enum):
    mini = "mini"
    small = "small"
    medium = "medium"
    large = "large"


class ProductDraft(BaseModel):
    """One bag model, as proposed by the model. A draft until a person reviews it."""

    # W03-D3: each description is sent to the model as part of the tool definition,
    # so the field rules live here and nowhere else.
    title: str = Field(
        min_length=10, max_length=70,
        description="Product name, 10 to 70 characters. No brand names.",
    )
    product_type: str = Field(
        description="Lowercase, e.g. tote, crossbody, clutch, backpack, shoulder bag, top-handle.",
    )
    # A list, because one group can hold the same model in several colours (bag-002).
    colours: list[Colour] = Field(
        min_length=1,
        description="Every colour the bag comes in across the photos, closest match from the list.",
    )
    material: str = Field(
        description="Lowercase. What it appears to be made of. Say 'leather-look' if you "
                    "can't tell real leather from faux.",
    )
    size: Size
    closure: str = Field(
        description="Lowercase, e.g. zip, magnetic snap, flap, open top. "
                    "'not visible' if the photo doesn't show it.",
    )
    description: str = Field(
        description="2 to 3 sentences for the product page. Describe only what is in the "
                    "photo - do not promise straps or parts that are not shown.",
    )
    seo_description: str = Field(
        max_length=160, description="One sentence, at most 160 characters.",
    )
    tags: list[str] = Field(  # on a list, max_length counts items
        max_length=10, description="3 to 10 short lowercase search words.",
    )


if __name__ == "__main__":
    from pydantic import ValidationError

    good = {
        "title": "Taupe Pebbled Structured Day Tote",
        "product_type": "tote",
        "colours": ["taupe", "tan"],
        "material": "pebbled faux leather",
        "size": "medium",
        "closure": "not visible",
        "description": "A structured tote with twin rolled top handles.",
        "seo_description": "Structured pebbled tote with twin handles.",
        "tags": ["tote", "structured", "everyday"],
    }

    print("Good record:")
    print(" ", ProductDraft(**good))

    bad_cases = {
        "11 tags": {**good, "tags": [f"tag{i}" for i in range(11)]},
        "title too short": {**good, "title": "Black Bag"},
        "SEO description too long": {**good, "seo_description": "x" * 161},
        "colour not in the list": {**good, "colours": ["purple"]},
        "no colours at all": {**good, "colours": []},
        "colour as text, not a list": {**good, "colours": "black"},
        "missing field": {k: v for k, v in good.items() if k != "material"},
    }

    for name, data in bad_cases.items():
        print(f"\n{name}:")
        try:
            ProductDraft(**data)
            print("  ACCEPTED - this should not happen")
        except ValidationError as e:
            for err in e.errors():
                field = ".".join(str(part) for part in err["loc"])
                print(f"  rejected - {field}: {err['msg']}")
