"""W03-D6 - check every .json file in a folder against ProductDraft.

Exits 0 if every file is valid, 1 if any file is rejected, so a script
(or CI later) can tell pass from fail without reading the output.

Run:  python validate_folder.py out/
"""

import sys
from pathlib import Path

from pydantic import ValidationError

from schema import ProductDraft

if len(sys.argv) != 2:
    raise SystemExit("Usage: python validate_folder.py <folder>")

folder = Path(sys.argv[1])
if not folder.is_dir():
    raise SystemExit(f"Not a folder: {folder}")

files = sorted(folder.glob("*.json"))
if not files:
    raise SystemExit(f"No .json files in {folder}")

rejected = 0
for path in files:
    try:
        # model_validate_json parses the text AND checks the rules in one step.
        # Broken JSON (a missing comma) is reported the same way, as field "(file)".
        ProductDraft.model_validate_json(path.read_text(encoding="utf-8"))
        print(f"OK        {path}")
    except ValidationError as e:
        rejected += 1
        print(f"REJECTED  {path}")
        for err in e.errors():
            field = ".".join(str(part) for part in err["loc"]) or "(file)"
            print(f"    {field}: {err['msg']}")

print(f"\n{len(files)} files | {len(files) - rejected} valid | {rejected} rejected")

# The exit code is the machine-readable answer: 0 = all good, anything else = problem.
sys.exit(1 if rejected else 0)
