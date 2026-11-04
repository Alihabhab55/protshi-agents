"""Turn sorted photo folders into bag-NNN_N.jpg files in photos/. No model call.

You decide which photos are the same bag by putting them in the same subfolder:

    photos_inbox/
        black pebbled tote/   IMG_1924.JPG.jpeg  IMG_1925.JPG.jpeg
        glitter clutch/       IMG_1928.JPG.jpeg  ...

Each subfolder becomes the next free bag-NNN. Photos are numbered _1, _2 ... in
filename order, so the first file is the main photo (rename it to "0 ..." to choose).
Folder names are only for you; they are written to rename_log.csv for reference.

Run:  python rename_photos.py              (dry run: shows the plan, copies nothing)
      python rename_photos.py --apply      (copies; originals in the inbox stay)
"""

import argparse
import csv
import hashlib
import re
import shutil
from pathlib import Path

from group_photos import PHOTO_NAME, group_photos
from images import extension_for, media_type_of

ALLOWED = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".webp": ".webp"}
MAX_BYTES = 5 * 1024 * 1024      # the API's per-image limit
LOG = Path("rename_log.csv")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def next_free_number(photos_dir):
    """The first bag number after the highest one already in photos/."""
    keys = group_photos(photos_dir).keys() if photos_dir.exists() else []
    numbers = [int(re.match(r"bag-(\d{3})", k).group(1)) for k in keys]
    return max(numbers, default=0) + 1


def build_plan(inbox, photos_dir):
    """Return (plan, problems). plan = [(bag_key, folder_name, [(src, dest_name)])]."""
    problems = []
    known = {sha256(p): p.name for p in photos_dir.iterdir()
             if p.is_file() and PHOTO_NAME.match(p.name)} if photos_dir.exists() else {}

    for loose in sorted(p for p in inbox.iterdir() if p.is_file()):
        problems.append(f"{loose.name}: not inside a bag folder - skipped")

    plan, number = [], next_free_number(photos_dir)
    for folder in sorted(p for p in inbox.iterdir() if p.is_dir()):
        bag_key = f"bag-{number:03d}"
        files = []
        for src in sorted(p for p in folder.iterdir() if p.is_file()):
            # The file's bytes decide the type, not its name: some ".PNG" photos are JPEGs.
            media_type = media_type_of(src)
            if media_type is None:
                problems.append(f"{folder.name}/{src.name}: not a JPEG/PNG/GIF/WebP image - skipped")
                continue
            ext = extension_for(media_type)
            if ext != ALLOWED.get(src.suffix.lower()):
                problems.append(f"{folder.name}/{src.name}: named {src.suffix} but really "
                                f"{media_type} - saved as {ext}")
            if src.stat().st_size > MAX_BYTES:
                problems.append(f"{folder.name}/{src.name}: over 5 MB - skipped")
                continue
            digest = sha256(src)
            if digest in known:
                problems.append(f"{folder.name}/{src.name}: same photo as {known[digest]} - skipped")
                continue
            known[digest] = src.name
            files.append((src, f"{bag_key}_{len(files) + 1}{ext}"))

        if not files:
            problems.append(f"{folder.name}/: no usable photos - no bag created")
            continue
        plan.append((bag_key, folder.name, files))
        number += 1
    return plan, problems


def main():
    parser = argparse.ArgumentParser(description="Copy sorted photo folders into photos/ as bag-NNN_N.")
    parser.add_argument("--inbox", default="photos_inbox", help="folder of bag subfolders")
    parser.add_argument("--photos", default="photos", help="destination (default: photos)")
    parser.add_argument("--apply", action="store_true", help="actually copy (default: dry run)")
    args = parser.parse_args()

    inbox, photos_dir = Path(args.inbox), Path(args.photos)
    if not inbox.is_dir():
        raise SystemExit(f"Not a folder: {inbox}")

    plan, problems = build_plan(inbox, photos_dir)

    for bag_key, folder_name, files in plan:
        print(f"{bag_key}  <-  {folder_name}/  ({len(files)} photo{'s' if len(files) > 1 else ''})")
        for src, dest in files:
            print(f"    {src.name:<24} -> {dest}")
    if problems:
        print("\nProblems:")
        for p in problems:
            print(f"  - {p}")

    total = sum(len(files) for _, _, files in plan)
    print(f"\n{len(plan)} bags, {total} photos, {len(problems)} problems")

    if not args.apply:
        print("Dry run - nothing copied. Add --apply to copy.")
        return

    photos_dir.mkdir(exist_ok=True)
    new_log = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_log:
            writer.writerow(["bag_key", "new_name", "original_name", "inbox_folder"])
        for bag_key, folder_name, files in plan:
            for src, dest in files:
                # copy2 keeps the file's original dates. The inbox copy stays put.
                shutil.copy2(src, photos_dir / dest)
                writer.writerow([bag_key, dest, src.name, folder_name])
    print(f"Copied {total} photos into {photos_dir}/ and logged them in {LOG}.")


if __name__ == "__main__":
    main()
