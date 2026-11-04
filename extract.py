"""W03-D4 to W04-D5 - extract every bag group into catalog.db; skip done work, survive failures.

Run:  python extract.py --limit 10
"""

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from catalog import connect, get_product, save_product
from group_photos import group_photos
from schema import ProductDraft

MODEL = "claude-opus-5"
# claude-opus-5 list prices, USD per million tokens. W07-D5 moves these to config.py.
INPUT_USD_PER_MTOK = 5.00
OUTPUT_USD_PER_MTOK = 25.00

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


def photos_hash(paths):
    """A fingerprint of the photos' bytes. Replace or add a photo -> a different hash."""
    h = hashlib.sha256()
    for path in paths:              # paths are already sorted by photo number
        h.update(Path(path).read_bytes())
    return h.hexdigest()


def cost_of(usage):
    return (usage.input_tokens * INPUT_USD_PER_MTOK
            + usage.output_tokens * OUTPUT_USD_PER_MTOK) / 1_000_000


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
    """Return (draft, None, cost_usd) on success or (None, error_text, cost_usd).

    cost_usd adds up every attempt - a retry is paid for too.
    Never raises for a bad answer - the caller can always move on to the next group.
    """
    cost_usd = 0.0
    messages = [{
        "role": "user",
        "content": [image_block(p) for p in paths]
                   + [{"type": "text", "text": "Describe this bag."}],
    }]

    for attempt in (1, 2):
        response = ask(client, messages)
        cost_usd += cost_of(response.usage)
        print(f"  attempt {attempt}: stop_reason={response.stop_reason}  "
              f"in={response.usage.input_tokens} out={response.usage.output_tokens}")

        tool_call = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_call is None:
            # Nothing to correct - there is no tool call to answer with an error.
            return None, f"no tool call (stop_reason={response.stop_reason})", cost_usd

        # 1. Validate every result against ProductDraft.
        try:
            return ProductDraft.model_validate(tool_call.input), None, cost_usd
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
    return None, error_text, cost_usd


def run(client, groups, con):
    """Extract every group into the database. One group failing never stops the others."""
    new, skipped, failed, total_cost = 0, 0, 0, 0.0
    started = time.perf_counter()          # a stopwatch: seconds since some fixed point
    width = len(str(len(groups)))

    for n, (group_key, paths) in enumerate(groups.items(), start=1):
        progress = f"[{n:>{width}}/{len(groups)}]"
        current_hash = photos_hash(paths)

        # W04-D4: check the database first.
        row = get_product(con, group_key)
        if row and row["status"] in ("extracted", "pushed") and row["photo_hash"] == current_hash:
            skipped += 1
            print(f"{progress} {group_key}: skipped (already {row['status']})")
            continue

        why = "new" if row is None else f"was {row['status']}"
        if row and row["photo_hash"] != current_hash and row["status"] != "failed":
            why = "photos changed"
        print(f"\n{progress} {group_key} ({len(paths)} photo{'s' if len(paths) > 1 else ''}, {why})")

        # W04-D5: each bag gets its own try/except. Anything unexpected for THIS bag
        # (network down, server error, unreadable photo) becomes a failed row, and the
        # loop moves on. Ctrl+C is not an Exception (it's KeyboardInterrupt), so it is
        # NOT caught here - pressing it still stops the run.
        try:
            draft, error, cost_usd = extract_group(client, group_key, paths)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
            # A bad key fails every bag the same way - stop instead of failing them all.
            raise
        except Exception as e:
            draft, error, cost_usd = None, f"{type(e).__name__}: {e}", 0.0
            print(f"  error: {error}")
        total_cost += cost_usd

        # Write the row straight away - success or failure - with what it cost.
        # save_product commits inside, so this bag is safe on disk before the next starts.
        if draft is not None:
            new += 1
            save_product(con, group_key, "extracted", draft, photo_hash=current_hash,
                         model_used=MODEL, cost_usd=cost_usd)
            print(f"  valid - {draft.title}  (${cost_usd:.4f})")
        else:
            failed += 1
            save_product(con, group_key, "failed", photo_hash=current_hash,
                         model_used=MODEL, cost_usd=cost_usd, error=error)
            print(f"  FAILED - saved as failed, moving on  (${cost_usd:.4f})")

    elapsed = time.perf_counter() - started
    minutes, seconds = divmod(elapsed, 60)
    print(f"\n{new} new | {skipped} skipped | {failed} failed | ${total_cost:.2f} "
          f"| {int(minutes)}m {seconds:.1f}s")
    return {"new": new, "skipped": skipped, "failed": failed, "cost_usd": total_cost,
            "seconds": elapsed}


def main():
    # argparse reads named options like --limit 10 and writes the --help text for us.
    parser = argparse.ArgumentParser(description="Extract a ProductDraft for each bag group.")
    parser.add_argument("folder", nargs="?", default="photos",
                        help="photo folder (default: photos)")
    parser.add_argument("--limit", type=int, default=None,
                        help="only process the first N groups")
    parser.add_argument("--db", default="catalog.db", help="database file (default: catalog.db)")
    args = parser.parse_args()

    if not Path(args.folder).is_dir():
        raise SystemExit(f"Not a folder: {args.folder}")

    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Check your .env file.")

    groups = group_photos(args.folder)
    if args.limit is not None:
        # Groups are sorted by key, so --limit 10 always means the same first ten.
        groups = dict(list(groups.items())[:args.limit])

    con = connect(args.db)
    try:
        run(anthropic.Anthropic(), groups, con)
    except KeyboardInterrupt:
        # Ctrl+C: every finished bag is already committed. Nothing to clean up.
        raise SystemExit("\nInterrupted. Finished bags are saved - run again to continue.")
    except anthropic.AuthenticationError:
        raise SystemExit("\nThe API key was rejected (401). Check ANTHROPIC_API_KEY in .env.")
    except anthropic.PermissionDeniedError as e:
        raise SystemExit(f"\nThe API refused this key (403): {e.message}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
