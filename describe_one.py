"""W02-D3 - send one bag photo to Claude and print the raw reply.

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

PROMPT = (
    "Look at the bag in this photo. Return a JSON object with exactly these keys: "
    '"name" (a short product name), "colour", "material", and "tags" '
    "(a list of 3 to 6 short lowercase words)."
)

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=2048,
    output_config={"effort": "low"},
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
                {"type": "text", "text": PROMPT},
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
