"""W06-D1 - one entry point for the whole pipeline.

    photos_inbox/  --ingest-->  photos/  --extract-->  catalog.db  --push-->  Shopify

Every stage reads and writes catalog.db, so each can run on its own, and 'all' is
just the three in a row. DRY RUN BY DEFAULT (the lesson of W05-D6): without --confirm
no photo is copied, no model is called and nothing reaches Shopify.

Run:  python run.py --stage extract --limit 3             (dry run: what would be extracted)
      python run.py --stage extract --limit 3 --confirm   (really extract up to 3 bags)
      python run.py --stage all --limit 10 --confirm      (ingest, extract, push: 10 each)
"""

import argparse
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

import extract
import push
import rename_photos
from catalog import connect, count_by_status
from group_photos import group_photos
from shopify_api import get_token

STAGES = ("ingest", "extract", "push")      # in pipeline order - 'all' runs them like this


def need_folder(path):
    if not Path(path).is_dir():
        raise SystemExit(f"Not a folder: {path}")


def stage_ingest(args, con, live):
    """photos_inbox/<bag folder>/ -> photos/bag-NNN_N.jpg, plus a 'pending' row per bag."""
    need_folder(args.inbox)
    return rename_photos.ingest(Path(args.inbox), Path(args.photos),
                                limit=args.limit, apply=live, con=con)


def stage_extract(args, con, live):
    """photos/ -> one ProductDraft row per bag. Skips bags already in the database."""
    need_folder(args.photos)
    groups = extract.first(group_photos(args.photos), args.limit)
    if not live:
        return extract.plan(groups, con)            # no client, no key, no call
    return extract.run(anthropic.Anthropic(), groups, con)


def stage_push(args, con, live):
    """catalog.db rows that are extracted and not yet pushed -> Shopify drafts."""
    need_folder(args.photos)
    photos = group_photos(args.photos)
    candidates = push.bags_to_push(con, [])         # [] = every extracted, unpushed bag
    token = get_token() if live else None           # a dry run never talks to Shopify
    return push.push_bags(con, photos, candidates, limit=args.limit, live=live, token=token)


RUN = {"ingest": stage_ingest, "extract": stage_extract, "push": stage_push}


def main():
    parser = argparse.ArgumentParser(
        description="Run the bag pipeline, one stage or all. DRY RUN unless --confirm.")
    parser.add_argument("--stage", required=True, choices=STAGES + ("all",),
                        help="which stage to run")
    parser.add_argument("--limit", type=int, default=None, help="at most N bags per stage")
    parser.add_argument("--inbox", default="photos_inbox", help="sorted photo folders")
    parser.add_argument("--photos", default="photos", help="renamed photos (default: photos)")
    parser.add_argument("--db", default="catalog.db", help="database file (default: catalog.db)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="show what would happen, change nothing (the default anyway)")
    mode.add_argument("--confirm", action="store_true",
                      help="really do it: copy photos, call the model, create products")
    args = parser.parse_args()
    live = args.confirm
    stages = list(STAGES) if args.stage == "all" else [args.stage]

    # Fail before doing anything, not halfway through: a live extract needs the key.
    # Shopify credentials are checked by get_token() when a live push starts.
    load_dotenv()
    if live and "extract" in stages and not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Check your .env file.")

    effects = {"ingest": "photos copied", "extract": "model called", "push": "products created"}
    print("LIVE RUN - " + ", ".join(effects[s] for s in stages) + "." if live else
          "DRY RUN - nothing will be copied, called or created. Add --confirm to run for real.")

    con = connect(args.db)
    try:
        for stage in stages:
            print(f"\n=== {stage} ({'live' if live else 'dry run'}) ===")
            RUN[stage](args, con, live)
        counts = count_by_status(con)
        print(f"\n{args.db}: " + (", ".join(f"{n} {status}" for status, n in counts.items())
                                   or "empty"))
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
