"""Shared test helpers: a fake Anthropic client and sample tool answers. No API calls."""

from types import SimpleNamespace

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
            usage=SimpleNamespace(input_tokens=1000, output_tokens=100),
            content=[SimpleNamespace(type="tool_use", id=f"toolu_{len(self.calls)}",
                                     input=tool_input)],
        )
