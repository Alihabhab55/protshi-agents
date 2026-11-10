# NOTES

What broke and what fixed it. One entry per thing, newest at the bottom.

## Week 1 — Foundations

- **`.env.example` was missing, so the D4 acceptance test failed.** Fixed by adding
  `.env.example` containing `ANTHROPIC_API_KEY=` with no value. `.env` itself is
  ignored by git and has never been committed — checked with `git status` and
  `git log --all --name-only`.

- **Empty key → no traceback, one line, nothing billed.** `load_dotenv()` read the
  file fine, but `os.getenv()` returned an empty string, so my own guard in
  `hello_claude.py` stopped the program before any network call happened.

- **Invalid key → `anthropic.AuthenticationError`, HTTP 401, `request_id: None`.**
  The key was present, so the guard let it through and Anthropic's server refused it.
  No `request_id` because a request that fails authentication never gets logged.
  Fixed by restoring the real key.

- **Wrong model name → `anthropic.NotFoundError`, HTTP 404, and a real `request_id`.**
  `claude-opus-6` does not exist. This request *was* authenticated, which is why it
  got an ID. Fixed by setting the model back to `claude-opus-5`.

- **Trap: `claude-opus-5-20260101` also 404s.** Never glue a date onto a model name.
  The correct ID is `claude-opus-5`, exactly as written.

- **How to read a traceback:** bottom-up. Ignore every frame with `site-packages` in
  the path — that is library code, not mine. Find the one line naming my own file.
  That line plus the last line is the whole diagnosis.

- **`output_tokens` costs 5× `input_tokens`** ($25 vs $5 per million). The first
  successful call was 46 in / 161 out ≈ $0.004.

## Week 2 — Data in, data out

- **JSON is text with strict rules.** Double quotes only, commas between pairs, no
  comma after the last one. `"tags"` is a real list (`[...]`), not one string with
  commas in it. `json.load` turns `{...}` into a `dict` and `[...]` into a `list`.

- **One missing comma → `json.decoder.JSONDecodeError: Expecting ',' delimiter:
  line 4 column 3`.** JSON is all-or-nothing: nothing loads. I removed the comma at
  the end of line 3, but the error pointed at line 4 — the parser reports where it
  *noticed* the problem (the next key), not where the mistake is. Rule: check the
  reported line **and the end of the line above it**.

- **Same traceback rule as week 1.** Frames under `Lib\json\` are Python's own code,
  skip them like `site-packages`. My line was `load_bag.py, line 4`.

- **Photos live in Google Drive, copied into `photos/`, never committed.** Drive
  desktop syncs to `G:\My Drive\Project`. `photos/` is in `.gitignore` — confirmed
  with `git check-ignore -v` and `git status`. Files are named `IMG_xxxx.JPG.jpeg`
  (double extension from iPhone export); use the last extension for the image type.

- **The org was put on hold → `anthropic.BadRequestError`, HTTP 400,
  `error_code: organization_on_hold`.** Not an expired or wrong key (that would be a
  401). The key was accepted and the request got a `request_id`; the *organization*
  was refused. Nothing in the code could fix it. Fixed by submitting a review request
  through the appeal link in the error. Nothing was billed.

- **W02·D3 first photo call worked: 1450 in / 82 out ≈ $0.009.** The image is most of
  the input tokens, so one photo call costs about twice my week 1 text call.

- **Prefill is gone on this model → HTTP 400 `This model does not support assistant
  message prefill. The conversation must end with a user message.`** The plan said to
  start the assistant turn with `{`. `claude-opus-5` rejects that before doing any work
  (free). Replacement: **structured outputs** — `output_config={"format": {"type":
  "json_schema", "schema": ...}}`. The API then guarantees the reply is valid JSON with
  exactly the schema's keys.

- **W02·D4 before vs after, same photo (`IMG_2417`, black quilted tote):**

  | | Before (D3) | After (D4) |
  |---|---|---|
  | Where the rules live | In the user message, next to the photo | `system=` prompt; user message is just "Describe this bag." |
  | Fields | 4 (name, colour, material, tags) | 9 (title, product_type, colour, material, size, closure, description, seo_description, tags) |
  | How JSON is enforced | Asked politely | Schema via structured outputs (prefill → 400) |
  | First character | `{` (got lucky — not guaranteed) | `{` (guaranteed) |
  | Preamble / code fence | None this time | None, and can't happen |
  | Formatting | Pretty-printed over several lines | One compact line |
  | Lowercase values | No: `"Black"`, `"Quilted leather"` | Yes: `"black"`, `"quilted leather"` |
  | Tokens / cost | 1450 in / 82 out ≈ $0.009 | 2102 in / 220 out ≈ $0.016 |

  Before:
  ```
  {"name": "Quilted Chevron Mini Tote", "colour": "Black",
   "material": "Quilted leather", "tags": ["tote", "quilted", "black", "leather", "handbag", "mini"]}
  ```
  After:
  ```
  {"title":"Chevron Quilted Leather Mini Tote","product_type":"tote","colour":"black",
   "material":"quilted leather","size":"small","closure":"zip", "description":"...",
   "seo_description":"...","tags":["tote","black","quilted","leather","zip","mini tote","handbag"]}
  ```

  Takeaways: the system prompt fixed the lowercase problem (a rule I stated, it
  followed). The schema made the format a guarantee instead of a hope. Cost went up
  because the system prompt and schema add ~650 input tokens and nine fields need more
  output. One new inconsistency: title says **"Mini"** but size says **"small"** — the
  schema checks the shape, not whether the values agree with each other.

- **W02·D5 parse safely.** `json.loads` raises `JSONDecodeError` on bad text; inside
  `try/except` that becomes a printed message + the raw text (`repr` so `\n` and empty
  strings are visible) and the function returns `None` instead of crashing. Tested with
  `python parse_reply.py` on 6 broken inputs — missing comma, "Here is the JSON:"
  preamble, ```` ```json ```` fence, cut-off reply, empty string, a list instead of an
  object — zero tracebacks. Preamble, fence and empty all say `Expecting value (line 1,
  column 1)`: the very first character isn't JSON. Still needed even with structured
  outputs, because a reply cut off by `max_tokens` or a refusal isn't complete JSON.

- **W02·D6 all 5 photos parsed, all 5 pass `python -m json.tool`.** Total ≈ $0.08.
  Raw replies saved in `evals/raw/`, findings in `evals/observations.md`. Biggest
  problems: material (leather vs faux is a guess every time), promised straps that
  aren't in the photo, and size with nothing for scale. Same photo gives a different
  title each run. Two photos (2429, 2433) are the same bag in two colours.

## Week 3 — Schema and validation

- **Photos renamed to `bag-NNN_N.jpg`** (in `photos/` only — Drive originals untouched).
  `bag-NNN` is the group key (one bag model), `_N` is the photo number, `_1` is the
  main photo. Three-digit IDs so `bag-010` sorts after `bag-009`. One group = one bag
  *model*: different angles **and** different colours of the same model go in the same
  group. Mapping from the week 2 names (`evals/raw/` still uses the old ones):

  | Old | New |
  |---|---|
  | IMG_2417 | bag-001_1.jpg |
  | IMG_2429 (taupe) | bag-002_1.jpg |
  | IMG_2433 (tan) | bag-002_2.jpg |
  | IMG_2431 | bag-003_1.jpg |
  | IMG_2461 | bag-004_1.jpg |

- **Why grouping is deterministic code, not a model's job.** The answer is already in
  the filename, so there's nothing to judge — only text to split at `_`.
  - *Same result every time.* `group_photos` puts `bag-002_2.jpg` in `bag-002` forever.
    A model doesn't: in week 2 the same photo got three different titles in three runs.
  - *Free and instant.* No API call, no tokens. A model would charge for every photo.
  - *A model would get it wrong.* bag-002's two photos are different colours — a model
    would likely split them. Two different black bags could look alike and be merged.
  - *Mistakes are visible and fixable.* If a bag is grouped wrong, the filename is wrong;
    rename it. A model's mistake has no cause you can point at.
  - *Testable with an exact answer.* A test can assert `bag-002` has exactly 2 photos.
  - Rule: **use the model only where judgment is needed (describing the bag). Anything
    with one correct answer — grouping, counting, sorting, checking a rule — is code.**

- **Files that don't match the pattern are skipped with a warning, never guessed.**
  Tested with `IMG_9999.jpg`, `notes.txt` and `bag-7_1.jpg` (only one digit). Photo
  numbers are compared as numbers, so `_10` sorts after `_2`, not after `_1`.

- **W03·D2 `ProductDraft` in `schema.py`.** pydantic was already installed (the
  anthropic SDK depends on it — it's in requirements.txt). Types say what *kind* of
  value; `Field(...)` adds limits: title 10–70 chars, seo_description ≤ 160, tags ≤ 10
  (on a list `max_length` counts items). `Colour` is an enum of 15 values;
  `colours` is a **list** of them (min 1) because one group can be one model in several
  colours. `size` is an enum too (mini/small/medium/large).
  11 tags → `ValidationError ... tags: List should have at most 10 items, not 11`.
  The error names the field — unlike W02·D1's `line 4 column 3`, no detective work.
  Gotcha: **taupe and tan are not in the colour list**, but 3 of my 4 bags are taupe
  or tan. `colours: ["taupe"]` is rejected. Decide: add them, or map them
  (taupe → beige/khaki, tan → brown).
  `describe_one.py` still asks for a single `colour` — W03·D3 will build the request
  from `ProductDraft` so there's only one definition.
  → Decided: **added `taupe` and `tan`** (17 colours). Most current stock is in those
  shades, and customers search for them by name.

- **W03·D3 extraction is now tool use.** `ProductDraft.model_json_schema()` becomes the
  tool's `input_schema` (tool `save_product_draft`), and
  `tool_choice={"type": "tool", "name": "save_product_draft"}` forces the model to call
  it — the answer arrives as `tool_use` with `.input` already a Python dict. Allowed on
  `claude-opus-5`; newer models (Opus 5.5 etc.) reject forced tool_choice with a 400,
  so a model switch later means `"auto"` + a prompt instruction.
  - **One definition, used twice:** the same class writes the request schema *and*
    validates the answer. The field rules moved from the system prompt into
    `Field(description=...)`, so they can't drift apart.
  - **Not `strict: true`:** strict tool schemas don't support `minLength`/`maxLength`.
    Without strict, those limits are sent as hints and **pydantic enforces them**
    afterwards. Bad answers print the field names and stop cleanly (W03·D4 adds retry).
  - **Deleted `parse_reply.py`** (the W02·D5 json.loads + try/except). No text to join,
    no json.loads, no fence to strip. The *idea* survives: look at the raw arguments
    first, then validate inside try/except.
  - **Two week 2 problems fixed by field descriptions:** material now says
    "leather-look" instead of guessing real vs faux, and the description no longer
    promises a strap that isn't in the photo.
  - bag-002_1: `stop_reason: tool_use`, 2731 in / 388 out ≈ $0.023 — dearer than week 2
    (≈ $0.016) because the schema with descriptions and 17 colours is bigger.

- **W03·D4 validate → retry once → fail cleanly, in `extract.py`.** Loops over
  `group_photos()` and sends **all photos of a group in one request**.
  - Every tool call goes through `ProductDraft.model_validate`.
  - On a `ValidationError` the conversation continues instead of starting over:
    `[user: photos] → [assistant: its tool_use] → [user: tool_result, is_error=True,
    "rejected: - tags: at most 10 items..."]`. `tool_use_id` links the error to the
    exact call. The model sees its own mistake and the reason, then calls the tool again.
  - Second failure → `(None, error)`; the group goes into `failed` and the loop moves
    on. One bad bag never stops the run.
  - **Tested without paying:** `test_retry.py` swaps in a fake client that returns
    pre-written answers (good / 11 tags then fixed / wrong twice / good). Result: 3 valid,
    1 failed, run continued, and the retry message really carried the error back.
    A real "impossible photo" is hard to produce on demand — the model usually manages
    *something* valid — so a fake model is the reliable way to test the failure path.
  - Real run: `4 groups | 4 valid | 0 failed`, no retries needed, ≈ $0.10 total.
    bag-002 (2 photos) costs ≈ 1,400 more input tokens — each extra photo ≈ $0.007.
  - `·` printed as `�` in the Windows terminal (console encoding) → used `|`.
  - `describe_one.py` is now a thin wrapper around `extract_group`, so there is only
    one prompt and one tool definition in the project.

- **W03·D5 drafts written to `out/bag-NNN.json`, `--limit` added.** Each valid draft
  is written the moment it passes (not at the end), so a later crash loses nothing.
  `model_dump_json` turns the enums back into plain strings. `argparse` handles
  `--limit`, `--out` and writes `--help` for free. `--limit` takes the first N groups
  *after sorting*, so it's always the same N. `out/` is in .gitignore — generated, and
  heading for SQLite in week 4.
  Run: `python extract.py --limit 10` → `4 groups | 4 valid | 0 failed` (only 4 groups
  exist; the plan's "10 valid" needs more photos). ≈ $0.10.
- **Read as a shop owner — two files:**
  - `bag-002` (2 photos): ✅ both colours found (`taupe`, `tan`) — sending the group
    together works. ❌ "panelled body" — that's bag-003, this one is plain. ⚠️ title
    "Grab Tote Handbag" says the same thing three times.
  - `bag-004`: ❌ colours `taupe` **and** `khaki` for a one-colour bag — it read the
    textured panel and the smooth trim as two colours. "colours" is ambiguous: *colours
    on the bag* or *colour versions sold*? I mean versions. ❌ "front **and back**
    panel" — the back isn't in the photo. 🔍 still misses the crystals on the handles.
  - Verdict: **not publishable as-is, good as drafts.** Each has 1–2 factual errors a
    customer could notice. This is exactly why everything goes to Shopify as a draft
    for a person to review (W05).

- **W03·D6 `validate_folder.py` — proving the validator actually rejects.**
  Hand-edited `out/bag-003.json` so `tags` was one string
  (`"taupe bag, top handle, ..."`) instead of a list. Result:
  ```
  REJECTED  out\bag-003.json
      tags: Input should be a valid array
  4 files | 3 valid | 1 rejected        exit code: 1
  ```
  Names the **file** and the **field**, exits **non-zero**. Says "array" (JSON's word)
  here but "list" (Python's word) in `schema.py` — `model_validate_json` reads JSON
  text, `model_validate` reads a Python dict. Same rule, different vocabulary.
  - Why the exit code matters: `0` = all good, anything else = problem. Scripts, CI
    and the scheduler in week 12 read the exit code, not the text.
  - A file with a missing comma is caught too, as `(file): Invalid JSON: expected ','
    or '}' at line 4 column 3` — the W02·D1 error again, now inside a report instead of
    a crash. The line is again the one *after* the missing comma.
  - Restored bag-003 afterwards → `4 valid | 0 rejected`, exit 0.
- **Week 3 acceptance — all free, no API calls:**
  - D1 `group_photos.py photos` → 4 groups, 5 photos, no model call ✅
  - D2 11 tags → `tags: List should have at most 10 items` ✅
  - D3 extraction returns tool arguments; no fence-stripping code left ✅
  - D4 `test_retry.py` → impossible bag marked failed, run continues ✅
  - D5 `extract.py --limit 10` → `4 groups | 4 valid | 0 failed`, 4 files in out/ ✅
    (plan says 10; only 4 groups exist)
  - D6 validator names file + field, exits 1 ✅
- **Open from D5:** `colours` is ambiguous (bag-004 got `taupe` + `khaki` for one
  colour). Fix the field description now or in W08·D5.

## Week 4 — SQLite catalog

- **W04·D1 SQL by hand.** `catalog.db` created with Python's built-in `sqlite3`;
  `practice` table, 3 rows typed by hand, queried with SELECT / WHERE / ORDER BY and
  checked in DB Browser. Forgetting `con.commit()` = rows silently lost. Close DB
  Browser before Python writes, or: `database is locked`. `*.db` is already ignored.

- **W04·D2 `products` table in `catalog.py`** — all SQL for the project lives there.
  One row per bag group: identity (`id`, `group_key`, `photo_hash`), the nine content
  fields, bookkeeping (`status`, `model_used`, `cost_usd`, `error`, `created_at`,
  `updated_at`, `shopify_product_id`).
  - **SQLite has no list type** → `colours` and `tags` are stored as JSON text
    (`'["taupe", "tan"]'`) and turned back into lists with `json.loads` when read.
  - **Content columns allow NULL** (empty): a failed bag has a row but no title.
  - **`status` has a `CHECK`** — only pending / extracted / failed / pushed. A typo
    like `'done'` → `IntegrityError: CHECK constraint failed`. Same idea as the Colour
    enum, enforced by the database itself.
  - **`group_key` is `NOT NULL`**; `UNIQUE` comes in W04·D3.
  - `photo_hash`: a fingerprint of the photos' bytes. If a photo is replaced, the hash
    changes → we know to extract again even though the filename didn't change.
  - `created_at` / `updated_at` default to `CURRENT_TIMESTAMP`, which is **UTC**, not
    Lebanon time (2–3 h behind local).
  - `CREATE TABLE IF NOT EXISTS` → running `catalog.py` twice is safe.
  - Constraint tests ran in `sqlite3.connect(":memory:")` — a throwaway database in
    RAM — so the real catalog.db stayed empty.

- **W04·D3 `group_key UNIQUE` + upsert (`save_product` in catalog.py).**
  - `UNIQUE` = the database refuses a second row with the same key:
    `IntegrityError: UNIQUE constraint failed: products.group_key`.
  - **Changing a table that already exists:** `CREATE TABLE IF NOT EXISTS` does
    nothing if the table is there, so adding UNIQUE to the code changed nothing in
    catalog.db. The table was empty, so I dropped it and let `connect()` recreate it.
    With real data that would be a *migration* — copy the rows into a new table. Do
    schema changes while tables are empty.
  - **Upsert** = `INSERT ... ON CONFLICT (group_key) DO UPDATE SET col = excluded.col`.
    `excluded` = the row I just tried to insert. One statement, no "does it exist?"
    check first. The SET list leaves out `id`, `created_at` and
    `shopify_product_id` on purpose — an update must never forget where the bag was
    pushed.
  - **Placeholders (`:title`, `?`), never pasted values.** sqlite3 fills them in
    safely. Pasting text into SQL breaks on the first apostrophe ("women's tote") and
    is how SQL injection happens. The test description contains an apostrophe on purpose.
  - `test_catalog.py` (in-memory DB): same group written twice → 1 row, second
    write's values, same id, same created_at, shopify id kept, lists come back as lists.
    A failed bag still gets a row with `status='failed'` and its error.
  - Gotcha: pydantic's `model_copy(update=...)` **skips validation** → serializer
    warning about `size`. Build changed drafts with `model_validate` instead.
  - Current behaviour: re-saving a bag as *failed* wipes its old content (row = latest
    attempt). Revisit in W04·D4 if that turns out wrong.

- **Old API key → `AuthenticationError` 401 `invalid x-api-key`.** `.env` hadn't
  changed since 30 Sep, no Windows env var was overriding it, format was fine — the key
  itself had been revoked (most likely during the account review). Fixed with a new key
  from the Console. **Credits belong to the account, not the key** — the $5 carried
  over. A 401 is checked before billing, so it says nothing about credits.
  The crash also showed an API error still kills the whole run → W04·D5.

- **W04·D4 check the database first, skip what's done.** For each group:
  `get_product()` → if status is `extracted`/`pushed` **and** `photo_hash` matches →
  skip, no API call. Otherwise extract, validate, `save_product()` with `cost_usd`
  (all attempts added up — a retry is paid for too). Failed bags are retried next run;
  a replaced photo changes the hash → extracted again. JSON files in `out/` dropped —
  the database is the one record now.
  - Fake-model test (`test_retry.py`): run 1 → 6 calls; run 2 → 1 call (only the
    failed bag); run 3 → **0 calls**; swapped photo → 1 call.
  - Real run 1: `4 new | 0 skipped | 0 failed | $0.10` (sum in db: $0.1021).
  - Real run 2: `0 new | 4 skipped | 0 failed | $0.00` in 1.7 s, **zero model calls**.
  - Cost per bag: ≈ $0.023 for one photo, $0.030 for two.

- **W04·D5 survive failure and interruption.**
  - **Each bag has its own try/except** around `extract_group`. Any `Exception` for
    that bag (network down, 5xx, unreadable photo) → row saved as `failed` with
    `"ConnectionError: network down"` in `error`, and the loop moves on.
  - **Except a bad key** (401 `AuthenticationError`, 403 `PermissionDeniedError`):
    it would fail every bag identically, so the run stops with one clear line instead
    of writing 104 identical failures. That's what happened with the revoked key.
  - **Ctrl+C is `KeyboardInterrupt`, which is *not* an `Exception`** (it's a
    `BaseException`), so `except Exception` doesn't swallow it — Ctrl+C still stops
    the run. `main()` catches it only to print "Interrupted. Finished bags are saved".
  - **Commit after each bag** was already true: `save_product` commits inside. So a
    finished bag is on disk before the next one starts; the interrupted bag leaves no
    half-written row and is simply extracted on the next run.
  - Cost of attempts made before an exception is lost (recorded as $0.00). Small, noted.
  - `test_resume.py` (fake model, in-memory DB): network error on bag 2 → 3 new / 1
    failed; Ctrl+C on bag 3 → bags 1–2 saved, no row for 3; restart → 2 skipped, 2 new,
    exactly 2 calls. Shared fake moved to `fakes.py` (importing a test file re-ran it).
  - **Real Ctrl+C test** (`--db resume_test.db`, deleted afterwards): pressed Ctrl+C
    while bag-002 was being extracted → "Interrupted. Finished bags are saved". Restart
    → `bag-001: skipped`, bag-002 extracted from scratch (no half row was left), then
    003–004 → `3 new | 1 skipped | 0 failed | $0.08`. Resumed, didn't start over. ✅
    Caveat: bag-002's interrupted request may still have been billed if Anthropic had
    already started it — an interrupted call can cost money without saving anything.

- **W04·D6 prep — 104 new photos, all with camera names (`IMG_1804.JPG.jpeg` …,
  97 jpeg + 7 PNG, largest 0.5 MB, no byte-for-byte duplicates).** Looked at three:
  IMG_1924 and IMG_1925 are the *same* black tote (detail + side), IMG_1928 is a
  different bag. So one photo ≠ one bag, and the filenames don't say which is which.
  Running them as 104 one-photo bags would cost ≈ $2.40 for wrong products. **Grouping
  is my decision, not the code's or a model's** (W03·D1 rule).
  - Moved the 104 into `photos_inbox/` (ignored by git); `photos/` keeps only
    `bag-NNN_N` files.
  - `rename_photos.py`: one **subfolder per bag** in the inbox → next free `bag-NNN`,
    photos `_1, _2…` in filename order (first = main photo). **Dry run by default**;
    `--apply` copies (inbox originals stay) and appends old→new to `rename_log.csv`.
    Skips with a reason: loose files, unsupported types, files over 5 MB, and photos
    identical to one already in `photos/` (so `--apply` twice is harmless).
  - `extract.py` now shows `[n/total]` and the elapsed time on the summary line.
    Its timer starts inside `run()`, so it excludes Python start-up (~1.5 s) —
    `Measure-Command` gives the full wall-clock number.

- **W04·D6 full batch — 104 new photos sorted into 22 bags (bag-005 … bag-026).**
  Sorted one folder per bag *model*, colours together; I checked the three uncertain
  ones (bag-007 white+black clutch, bag-016 incl. IMG_2014, bag-023 alone) — all right.
  `rename_photos.py --apply` → 104 copied, old→new in `rename_log.csv`. Originals in
  `photos_inbox/`, plus a full copy in `photos_inbox_backup/` (both ignored by git).
  ⚠️ The originals were *moved* out of Google Drive, not copied — no cloud backup yet.

  **The numbers to quote** (claude-opus-5, effort low, 5 Nov 2026):

  | | |
  |---|---|
  | Catalog | 26 bags, 109 photos (1–12 photos per bag) |
  | New this batch | 22 bags, 104 photos |
  | Result | 22 / 22 extracted (4 after a fix, 1 needed a retry) |
  | Cost, 22 new bags | **$1.26** → **$0.057 per bag** (≈ $0.012 per photo) |
  | Cost, whole catalog | $1.36 for 26 bags, avg $0.052, max $0.215 (bag-022) |
  | Wall-clock, 22 bags | ≈ 2 min 35 s (2m 01s + 34s) → **≈ 7 s per bag** |
  | Second run | `0 new | 26 skipped | 0 failed | $0.00` in **1.65 s** ✅ |

  - **7 files named `.PNG` were really JPEGs.** The code took the type from the
    extension; the API checks the bytes → `400 ... specified using the image/png media
    type, but the image appears to be a image/jpeg image`. 4 bags failed, the run
    carried on (W04·D5 working), cost $0.00. Fix: `images.py` reads the type from the
    file's first bytes (JPEG starts `FF D8 FF`, PNG `89 50 4E 47`); `extract.py` and
    `rename_photos.py` use it. Renamed the 7 to `.jpg`; rerun → only the 4 failed bags
    were extracted.
  - **A real retry:** bag-022 attempt 1 said `colours: ["champagne"]` (not in the
    enum) → error sent back → attempt 2 valid. Cost $0.215 — 12 photos sent twice.
    Many photos × a retry = the expensive case.
  - Cost grows with photos, not bags: 1 photo ≈ $0.023, 4 ≈ $0.045, 12 ≈ $0.10.
  - **The colours field is still ambiguous** (open since W03·D5): hardware and trim
    get counted as colours — bag-007 `white, silver, black`, bag-009 `black, silver`,
    bag-024 `beige, khaki, taupe` for one canvas tote. Fix in W08·D5.
  - Week 4 acceptance: second run `0 new | 26 skipped | $0.00` under two seconds ✅

## Week 5 — Shopify push

- **W05·D1 Shopify app — the plan's method no longer exists.** Since 1 Jan 2026
  Shopify doesn't let you create new custom apps under *Settings → Apps → Develop apps*,
  and new apps never show a `shpat_` token. Instead:
  - Created `protshi-agents` in the **Dev Dashboard** (dev.shopify.com), scopes
    `read_products,write_products` only, App URL left as `https://example.com`, embed
    unticked. Version `v1-products-only` released → **Overview → Install app** → PROTSHI.
  - After install Shopify opened `example.com` — that's just the placeholder App URL;
    the app has no screens. Harmless.
  - `.env` gets `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`;
    the names (no values) are in `.env.example`.
  - The code trades ID + secret for a token: `POST https://<store>/admin/oauth/access_token`
    with `grant_type=client_credentials` → token valid **24 h** (`expires_in: 86399`).
    Only works because app and store are in the same organization.
  - **Gotcha: the store domain is the *handle*, not the shop name.** The admin URL
    `admin.shopify.com/store/protshi-2` → `protshi-2.myshopify.com`. With the placeholder
    domain Shopify answered `404 Store unavailable` — a wrong address, not wrong secrets.
  - Test: HTTP 200, `scope granted: write_products`, token received. Shopify lists only
    `write_products` because write access includes read access.
  - **Least privilege:** only product scopes. If these credentials leak, customers'
    names, phones and addresses are still out of reach.

- **W05·D2 read one product — switched to the GraphQL Admin API** (REST is legacy;
  product REST resources deprecated since 2024-04). `shopify_api.py` holds all Shopify
  code (token, `graphql()`, `check()`), like catalog.py holds all SQL.
  `python shopify_read.py` → **200, no `errors`** — read access works (write includes read).
  - **GraphQL always uses POST**, even to read: the query travels in the body. One
    address for everything: `/admin/api/2026-10/graphql.json`.
  - **GraphQL can fail inside a 200** — a bad field name gives 200 +
    `{"errors": [...]}`. "Done" = status 200 **and** no `errors`. `check()` tests both.
  - You get only the fields you ask for. Cost of this query: 17 points out of a
    2,000-point bucket that refills 100 points/second (`extensions.cost`).
  - **Shape of a product, and what W05·D3 must send:**

    | Field | Example | Note |
    |---|---|---|
    | `id` | `gid://shopify/Product/8937253732638` | **text**, not a number → `shopify_product_id` column should be TEXT (W05·D5) |
    | `title` | `Emma Heels` | |
    | `status` | `ARCHIVED` | GraphQL uses UPPERCASE: ACTIVE / DRAFT / ARCHIVED. Ours: always `DRAFT` |
    | `descriptionHtml` | `<p>...</p><ul><li>...` | HTML, not plain text |
    | `productType` | `""` | empty — the store doesn't use it |
    | `vendor` | `Protshi Garments` | |
    | `tags` | `["all", "Collection Beta", "heels"]` | **a list** in GraphQL (REST used one string) — matches ours |
    | `options` | Color [Black, Pink], Size [36–40], Heel [7cm, 9cm] | **how the store models colours** |
    | `variants.nodes[].price` | `"25.00"` | price lives on the **variant**, as a string |
    | `variants.nodes[].sku` | `9B4A8147` | |
    | `media.nodes[].image.url` | `https://cdn.shopify.com/...` | |

  - **The store already does colours as variants:** a `Color` option, and one variant
    per combination (`Black / 36 / 7cm`). That answers the W03·D2 question — our
    `colours` list maps naturally to a Color option.
  - `�` in the printed description: the Windows terminal can't show some characters
    (an em dash, a non-breaking space). Display only — the data is fine. Will matter for
    Arabic in week 10 (fix: `PYTHONIOENCODING=utf-8`).

- **W05·D3 first write — one hardcoded draft.** `shopify_create_one.py` →
  `productCreate` mutation → `gid://shopify/Product/16072089829662`,
  "TEST - Protshi agent draft - delete me", status `DRAFT`, 1 variant at `0.00`.
  - **A mutation is a GraphQL write**; values go in `variables` (`$product`), never
    pasted into the query text — same idea as SQL placeholders.
  - `productCreate` always makes exactly **one initial variant**, price `0.00` by
    default. More variants (colours) need `productVariantsBulkCreate` or `productSet`.
  - New products are **unpublished** (no sales channel) as well as DRAFT — invisible
    to customers twice over.
  - The plan expected **201 Created** (REST). GraphQL answers **200** for everything;
    success is read from the body.
  - **Three layers of "did it work?"** for a GraphQL mutation:
    1. HTTP status 200 (else: network/auth/address problem)
    2. no top-level `errors` (else: the query itself is broken)
    3. empty `userErrors` (else: Shopify understood but refused the *change*)
  - Every run creates a **new** product. No duplicate protection until W05·D5.

- **W05·D4 photos — not base64 in the request (that was REST).** GraphQL does it in
  three steps, in `shopify_api.upload_image` + `push.py`:
  1. `stagedUploadsCreate` (resource `IMAGE`, `httpMethod: PUT`) → an upload slot:
     `url`, `resourceUrl`, and `parameters` (headers to send along)
  2. `PUT` the file's bytes to `url` — straight to Shopify's storage, not via the API
  3. `productCreate(product, media=[{originalSource: resourceUrl, ...}])` — **the order
     of the media list is the photo order**, so `_1` is the main photo.
  Shopify then processes photos in the background (UPLOADED → PROCESSING → READY);
  `push.py` polls until all are READY or FAILED, max 30 s.
  - **429 handling** in `shopify_api.graphql`: Shopify says "slow down" as HTTP 429
    *or* as a 200 with `errors[].extensions.code == "THROTTLED"`. Either way: wait
    `Retry-After` seconds (else 2, 4, 8 — backing off) and retry, max 4 attempts.
    Plus a 1 s `PAUSE_SECONDS` between products.
  - Description goes through `html.escape()` before `<p>…</p>` — a `<` or `&` in a
    description would otherwise break the HTML.
  - Also sent: SEO title + description (`seo`), alt text on every photo.
  - Pushed **bag-002** (2 photos): `gid://shopify/Product/16072100905246`, DRAFT, 0.00,
    photos `bag-002_1.jpg`, `bag-002_2.jpg` in that order, both READY.
