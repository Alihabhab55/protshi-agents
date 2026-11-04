"""W03-D4/W04-D4 - prove the retry and skip logic with a fake model. No API call, no cost.

Run:  python test_retry.py
"""

from catalog import connect, get_product
from extract import run
from fakes import ELEVEN_TAGS, GOOD, PURPLE, FakeClient


groups = {
    "bag-101": ["photos/bag-001_1.jpg"],   # fine first time
    "bag-102": ["photos/bag-001_1.jpg"],   # 11 tags, then fixed on retry
    "bag-103": ["photos/bag-001_1.jpg"],   # "impossible": wrong twice
    "bag-104": ["photos/bag-001_1.jpg"],   # fine - proves the run continued
}
con = connect(":memory:")       # throwaway database, catalog.db is never touched
client = FakeClient([GOOD, ELEVEN_TAGS, GOOD, PURPLE, PURPLE, GOOD])

summary = run(client, groups, con)

assert summary["new"] == 3 and summary["failed"] == 1, summary
assert len(client.calls) == 6, len(client.calls)    # 1 + 2 + 2 + 1
assert get_product(con, "bag-103")["status"] == "failed"
assert "title" in get_product(con, "bag-103")["error"]

# Cost: every call is 1,000 in / 100 out = $0.0075. bag-102 needed two calls.
assert abs(get_product(con, "bag-101")["cost_usd"] - 0.0075) < 1e-9
assert abs(get_product(con, "bag-102")["cost_usd"] - 0.0150) < 1e-9

# W04-D4: second run. Extracted bags are skipped with no call; the failed one is retried.
print("\n--- second run ---")
client_2 = FakeClient([GOOD])
summary_2 = run(client_2, groups, con)
assert {k: summary_2[k] for k in ("new", "skipped", "failed", "cost_usd")} == {"new": 1, "skipped": 3, "failed": 0, "cost_usd": 0.0075}, summary_2
assert len(client_2.calls) == 1                      # only bag-103
assert get_product(con, "bag-103")["status"] == "extracted"

# Third run: everything is done, so zero calls.
print("\n--- third run ---")
client_3 = FakeClient([])
summary_3 = run(client_3, groups, con)
assert summary_3["skipped"] == 4 and len(client_3.calls) == 0

# Fourth run: bag-101 gets a different photo -> new hash -> extracted again.
print("\n--- fourth run, bag-101's photo replaced ---")
groups["bag-101"] = ["photos/bag-002_1.jpg"]
client_4 = FakeClient([GOOD])
summary_4 = run(client_4, groups, con)
assert summary_4["new"] == 1 and summary_4["skipped"] == 3 and len(client_4.calls) == 1

# The retry for bag-102 (call 3) must carry the error back to the model.
retry = client.calls[2]["messages"]
assert [m["role"] for m in retry] == ["user", "assistant", "user"]
tool_result = retry[2]["content"][0]
assert tool_result["type"] == "tool_result" and tool_result["is_error"] is True
assert tool_result["tool_use_id"] == "toolu_2"
assert "tags" in tool_result["content"]

print("\nAll retry checks passed.")
