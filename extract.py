"""W03-D4 - extract a ProductDraft for every bag group, retry once, never stop the run.

Run:  python extract.py photos
"""

import base64
import json
import mimetypes
import os
import sys

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from group_photos import group_photos
from schema import ProductDraft

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You write product listings for an online bag store.
Look at the bag in the photos and record it with the save_product_draft tool.
All photos you receive show the same bag model, possibly from different angles
and in different colours.
Only describe what you can see in the photos. Do not invent a brand."""

SAVE_TOOL = {
    "name": "save_product_draft",
    "description": "Save the product listing draft for the bag in the photos.",
    "input_schema": ProductDraft.model_json_schema(),
}


def image_block(path):
    """One photo as a base64 image content block."""
    media_type, _ = mimetypes.guess_type(path)
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


def ask(client, messages):
    return client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        tools=[SAVE_TOOL],
        tool_choice={"type": "tool", "name": "save_product_draft"},
        messages=messages,
    )


def describe_errors(e):
    """A ValidationError as short lines a person - or the model - can act on."""
    lines = []
    for err in e.errors():
        field = ".".join(str(part) for part in err["loc"]) or "(whole record)"
        lines.append(f"    - {field}: {err['msg']}")
    return "\n".join(lines)


def extract_group(client, group_key, paths):
    """Return (draft, None) on success or (None, error_text) after two failed attempts.

    Never raises for a bad answer - the caller can always move on to the next group.
    """
    messages = [{
        "role": "user",
        "content": [image_block(p) for p in paths]
                   + [{"type": "text", "text": "Describe this bag."}],
    }]

    for attempt in (1, 2):
        response = ask(client, messages)
        print(f"  attempt {attempt}: stop_reason={response.stop_reason}  "
              f"in={response.usage.input_tokens} out={response.usage.output_tokens}")

        tool_call = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_call is None:
            # Nothing to correct - there is no tool call to answer with an error.
            return None, f"no tool call (stop_reason={response.stop_reason})"

        # 1. Validate every result against ProductDraft.
        try:
            return ProductDraft.model_validate(tool_call.input), None
        except ValidationError as e:
            error_text = describe_errors(e)
            print(f"  attempt {attempt} broke the rules:\n{error_text}")

        # 2. Send the error back once. The conversation must stay in order:
        # our photos -> the model's tool call -> our tool_result saying what was wrong.
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_call.id,   # links this result to that exact call
                "is_error": True,
                "content": "The draft was rejected by validation:\n" + error_text
                           + "\nCall save_product_draft again with every problem fixed.",
            }],
        })
        # Raw arguments, so you can see what it actually sent.
        print(f"  rejected input: {json.dumps(tool_call.input)}")

    # 3. Two failures: give up on this group, but only this group.
    return None, error_text


def run(client, groups):
    """Extract every group. One group failing never stops the others."""
    valid, failed = {}, {}
    for group_key, paths in groups.items():
        print(f"\n{group_key} ({len(paths)} photo{'s' if len(paths) > 1 else ''})")
        draft, error = extract_group(client, group_key, paths)
        if draft is not None:
            valid[group_key] = draft
            print(f"  valid - {draft.title}")
        else:
            failed[group_key] = error
            print(f"  FAILED - recorded, moving on")

    print(f"\n{len(groups)} groups | {len(valid)} valid | {len(failed)} failed")
    for group_key, error in failed.items():
        print(f"  {group_key}: {error.splitlines()[0].strip()}")
    return valid, failed


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python extract.py <photo_folder>")

    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Check your .env file.")

    run(anthropic.Anthropic(), group_photos(sys.argv[1]))


if __name__ == "__main__":
    main()
