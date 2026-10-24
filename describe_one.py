"""W02-D3/D4 - send one bag photo to Claude and print the raw reply as JSON only.

Run:  python describe_one.py photos/IMG_2417.JPG.jpeg
"""

import base64
import mimetypes
import os
import sys

import anthropic
from dotenv import load_dotenv

# 1. Read the image path from the command line.
# sys.argv[0] is this script's name, sys.argv[1] is the path typed after it.
if len(sys.argv) != 2:
    raise SystemExit("Usage: python describe_one.py <image_path>")

image_path = sys.argv[1]

if not os.path.exists(image_path):
    raise SystemExit(f"File not found: {image_path}")

# guess_type looks at the LAST extension only, so "IMG_2417.JPG.jpeg" -> image/jpeg.
media_type, _ = mimetypes.guess_type(image_path)
if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
    raise SystemExit(f"Not a supported image type: {media_type}")

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("ANTHROPIC_API_KEY is not set. Check your .env file.")

# 2. Base64-encode the image.
# The API only accepts text (JSON), so the photo's raw bytes are turned into
# a long string of plain letters and digits first.
with open(image_path, "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

client = anthropic.Anthropic()

# W02-D4: the field list lives in the system prompt, not in the user message.
# The system prompt holds the standing rules; the user message holds only the photo.
SYSTEM_PROMPT = """You write product listings for an online bag store.
Look at the bag in the photo and describe it using exactly these nine fields:

1. title - a product name, 10 to 70 characters.
2. product_type - one word or short phrase, e.g. tote, crossbody, clutch, backpack.
3. colour - the main colour, one word.
4. material - what the bag appears to be made of.
5. size - one of: mini, small, medium, large.
6. closure - how it closes, e.g. zip, magnetic snap, flap, open top. Use "not visible" if you can't see it.
7. description - 2 to 3 sentences for the product page, plain English.
8. seo_description - one sentence, at most 160 characters.
9. tags - 3 to 10 short words.

Write every value in lowercase except title and description.
Only describe what you can see in the photo. Do not invent a brand."""

# W02-D4: prefill ("start the reply with {") returns a 400 on this model.
# Structured outputs replace it: the API guarantees the reply is JSON
# matching this schema - no preamble, no code fence, no missing keys.
BAG_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "product_type": {"type": "string"},
        "colour": {"type": "string"},
        "material": {"type": "string"},
        "size": {"type": "string", "enum": ["mini", "small", "medium", "large"]},
        "closure": {"type": "string"},
        "description": {"type": "string"},
        "seo_description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "title", "product_type", "colour", "material", "size",
        "closure", "description", "seo_description", "tags",
    ],
    "additionalProperties": False,
}

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=2048,
    system=SYSTEM_PROMPT,
    output_config={
        "effort": "low",
        "format": {"type": "json_schema", "schema": BAG_SCHEMA},
    },
    messages=[
        {
            "role": "user",
            "content": [
                # The image goes before the text that asks about it.
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": "Describe this bag."},
            ],
        }
    ],
)

# 3. Print the raw reply exactly as it comes back - no json.loads, no cleanup.
for block in response.content:
    if block.type == "text":
        print(block.text)

print(
    f"\nstop_reason: {response.stop_reason}  "
    f"input tokens: {response.usage.input_tokens}  "
    f"output tokens: {response.usage.output_tokens}"
)
