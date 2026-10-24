"""W03-D1 - group photos into bags by filename. No model call.

Convention:  bag-014_1.jpg  ->  group key "bag-014", photo number 1.

Run:  python group_photos.py photos
"""

import re
import sys
from pathlib import Path

# bag- + exactly 3 digits, then _ + photo number, then an image extension.
# re.IGNORECASE so .JPG and .jpg are treated the same.
PHOTO_NAME = re.compile(r"^(bag-\d{3})_(\d+)\.(jpg|jpeg|png|webp)$", re.IGNORECASE)


def group_photos(folder):
    """Return {group_key: [paths]}, each list sorted by photo number (_1 first).

    Files that don't match the convention are skipped with a warning, never guessed.
    """
    groups = {}

    for path in Path(folder).iterdir():
        if not path.is_file():
            continue

        match = PHOTO_NAME.match(path.name)
        if match is None:
            print(f"Skipping {path.name}: does not match bag-NNN_N.jpg")
            continue

        group_key = match.group(1)            # "bag-002"
        photo_number = int(match.group(2))    # 2  (a number, so 10 sorts after 9)

        # setdefault: create an empty list the first time we see this bag.
        groups.setdefault(group_key, []).append((photo_number, str(path)))

    # Sort the bags by key, and each bag's photos by number, then drop the numbers.
    return {
        key: [p for _, p in sorted(photos)]
        for key, photos in sorted(groups.items())
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python group_photos.py <folder>")

    folder = sys.argv[1]
    if not Path(folder).is_dir():
        raise SystemExit(f"Not a folder: {folder}")

    groups = group_photos(folder)
    for key, paths in groups.items():
        print(f"{key}: {paths}")
    print(f"\n{len(groups)} groups, {sum(len(p) for p in groups.values())} photos")
