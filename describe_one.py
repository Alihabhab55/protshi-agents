"""Describe a single photo - handy for trying one bag by hand.

The real work lives in extract.py (one prompt, one tool, one retry rule).

Run:  python describe_one.py photos/bag-001_1.jpg
"""

import mimetypes
import os
import sys

import anthropic
from dotenv import load_dotenv

from extract import extract_group

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

draft, error = extract_group(anthropic.Anthropic(), image_path, [image_path])
if draft is None:
    raise SystemExit(f"Failed after two attempts:\n{error}")

print(draft.model_dump_json(indent=2))
