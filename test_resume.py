"""W04-D5 - one bag's error doesn't stop the run, and Ctrl+C halfway resumes cleanly.

Fake model, in-memory database: no API call, no cost.
Run:  python test_resume.py
"""

from catalog import connect, get_product
from extract import run
from fakes import GOOD, FakeClient


class RaisingClient(FakeClient):
    """Like FakeClient, but an answer that is an exception gets raised instead."""

    def create(self, **request):
        if isinstance(self.answers[0], BaseException):
            self.calls.append(request)
            raise self.answers.pop(0)
        return super().create(**request)


groups = {f"bag-20{i}": ["photos/bag-001_1.jpg"] for i in range(1, 5)}

# 1. A network error on bag-202 -> bag-202 saved as failed, the run carries on.
print("=== run with a network error on the 2nd bag ===")
con = connect(":memory:")
summary = run(RaisingClient([GOOD, ConnectionError("network down"), GOOD, GOOD]), groups, con)
assert summary["new"] == 3 and summary["failed"] == 1, summary
row = get_product(con, "bag-202")
assert row["status"] == "failed" and row["error"] == "ConnectionError: network down", row

# 2. Ctrl+C while bag-203 is being extracted.
print("\n=== run interrupted by Ctrl+C on the 3rd bag ===")
con = connect(":memory:")
try:
    run(RaisingClient([GOOD, GOOD, KeyboardInterrupt()]), groups, con)
    raise AssertionError("Ctrl+C was swallowed - it must stop the run")
except KeyboardInterrupt:
    print("  ...stopped by Ctrl+C")

saved = [r["group_key"] for r in con.execute("SELECT group_key FROM products")]
assert saved == ["bag-201", "bag-202"], saved     # finished bags were already committed
assert get_product(con, "bag-203") is None         # the interrupted one left no half row

# 3. Restart: the two finished bags are skipped, only the last two are extracted.
print("\n=== restart ===")
restart = FakeClient([GOOD, GOOD])
summary = run(restart, groups, con)
assert summary == {"new": 2, "skipped": 2, "failed": 0, "cost_usd": 0.015}, summary
assert len(restart.calls) == 2

print("\nAll resume checks passed.")
