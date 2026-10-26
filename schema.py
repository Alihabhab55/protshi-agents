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

    title: str = Field(min_length=10, max_length=70)
    product_type: str
    # A list, because one group can hold the same model in several colours (bag-002).
    colours: list[Colour] = Field(min_length=1)
    material: str
    size: Size
    closure: str
    description: str
    seo_description: str = Field(max_length=160)
    tags: list[str] = Field(max_length=10)  # on a list, max_length counts items


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
