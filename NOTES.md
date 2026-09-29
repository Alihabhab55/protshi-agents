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
