"""W03-D4 - prove the retry logic with a fake model. No API call, no cost.

Run:  python test_retry.py
"""

from types import SimpleNamespace

from extract import run

GOOD = {
    "title": "Taupe Pebbled Structured Day Tote",
    "product_type": "tote",
    "colours": ["taupe"],
    "material": "leather-look",
    "size": "medium",
    "closure": "not visible",
    "description": "A structured tote with twin rolled top handles.",
    "seo_description": "Structured pebbled tote with twin handles.",
    "tags": ["tote", "structured"],
}
ELEVEN_TAGS = {**GOOD, "tags": [f"tag{i}" for i in range(11)]}
PURPLE = {**GOOD, "colours": ["purple"], "title": "Bag"}


class FakeClient:
    """Stands in for anthropic.Anthropic(). Hands out pre-written answers in order."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **request):
        self.calls.append(request)
        tool_input = self.answers.pop(0)
        return SimpleNamespace(
            stop_reason="tool_use",
            usage=SimpleNamespace(input_tokens=0, output_tokens=0),
            content=[SimpleNamespace(type="tool_use", id=f"toolu_{len(self.calls)}",
                                     input=tool_input)],
        )


groups = {
    "bag-101": ["photos/bag-001_1.jpg"],   # fine first time
    "bag-102": ["photos/bag-001_1.jpg"],   # 11 tags, then fixed on retry
    "bag-103": ["photos/bag-001_1.jpg"],   # "impossible": wrong twice
    "bag-104": ["photos/bag-001_1.jpg"],   # fine - proves the run continued
}
client = FakeClient([GOOD, ELEVEN_TAGS, GOOD, PURPLE, PURPLE, GOOD])

valid, failed = run(client, groups)

assert sorted(valid) == ["bag-101", "bag-102", "bag-104"], valid
assert list(failed) == ["bag-103"], failed
assert len(client.calls) == 6, len(client.calls)    # 1 + 2 + 2 + 1

# The retry for bag-102 (call 3) must carry the error back to the model.
retry = client.calls[2]["messages"]
assert [m["role"] for m in retry] == ["user", "assistant", "user"]
tool_result = retry[2]["content"][0]
assert tool_result["type"] == "tool_result" and tool_result["is_error"] is True
assert tool_result["tool_use_id"] == "toolu_2"
assert "tags" in tool_result["content"]

print("\nAll retry checks passed.")
