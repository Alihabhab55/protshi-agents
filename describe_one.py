"""W02-D3 to W03-D3 - send one bag photo to Claude and get a validated ProductDraft back.

Run:  python describe_one.py photos/bag-001_1.jpg
"""

import base64
import json
import mimetypes
import os
import sys

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from schema import ProductDraft

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

# The system prompt keeps only the general rules. The per-field rules now live in
# ProductDraft's Field descriptions, which travel inside the tool definition.
SYSTEM_PROMPT = """You write product listings for an online bag store.
Look at the bag in the photo and record it with the save_product_draft tool.
Only describe what you can see in the photo. Do not invent a brand."""

# W03-D3: ProductDraft becomes a tool. model_json_schema() writes the JSON schema
# from the pydantic class - field names, types, the colour list, the descriptions.
# One definition, used twice: to ask the model, and to check its answer.
SAVE_TOOL = {
    "name": "save_product_draft",
    "description": "Save the product listing draft for the bag in the photo.",
    "input_schema": ProductDraft.model_json_schema(),
}

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=2048,
    system=SYSTEM_PROMPT,
    output_config={"effort": "low"},
    tools=[SAVE_TOOL],
    # Force this exact tool: the model must fill in its arguments, not write text.
    tool_choice={"type": "tool", "name": "save_product_draft"},
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

print(
    f"stop_reason: {response.stop_reason}  "
    f"input tokens: {response.usage.input_tokens}  "
    f"output tokens: {response.usage.output_tokens}"
)

# 3. Find the tool call. Its .input is already a Python dict - the SDK parsed it.
# No text to join, no json.loads, no code fence to strip.
tool_call = next((b for b in response.content if b.type == "tool_use"), None)
if tool_call is None:
    raise SystemExit("Stopping: the model did not call save_product_draft.")

# Still look at the raw arguments first, before trusting them.
print(json.dumps(tool_call.input, indent=2))

# 4. The tool guarantees the shape. pydantic checks the rules: lengths, 10 tags,
# colours from the list. A failure prints the field names instead of crashing.
try:
    draft = ProductDraft.model_validate(tool_call.input)
except ValidationError as e:
    print("\nThe model's answer broke the rules:")
    for err in e.errors():
        field = ".".join(str(part) for part in err["loc"])
        print(f"  {field}: {err['msg']}")
    raise SystemExit("Stopping: invalid ProductDraft.")

print(f"\nValid ProductDraft - title: {draft.title}")
