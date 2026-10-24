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
