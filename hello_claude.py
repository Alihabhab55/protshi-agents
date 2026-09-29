"""W01-D5 - the first real call to the Claude API.

Run:  python hello_claude.py
"""

import os

import anthropic
from dotenv import load_dotenv

# Reads .env from this folder and loads ANTHROPIC_API_KEY into the environment.
# The key itself never appears in this file.
load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    raise SystemExit("ANTHROPIC_API_KEY is not set. Check your .env file.")

# No api_key= argument. The SDK picks the key up from the environment itself.
client = anthropic.Anthropic()

PROMPT = (
    "Write one short paragraph for an online store describing a black leather "
    "crossbody bag. Plain English, no bullet points, no headings."
)

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=2048,          # a ceiling, not a target - you only pay for what comes back
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": PROMPT}],
)

# response.content is a LIST of blocks, not a string. Claude can return
# thinking blocks next to the text, so check .type before reading .text.
for block in response.content:
    if block.type == "text":
        print(block.text)

# output_tokens counts everything Claude generated, thinking included.
print(
    f"\ninput tokens: {response.usage.input_tokens}  "
    f"output tokens: {response.usage.output_tokens}"
)
