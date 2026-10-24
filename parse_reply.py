"""W02-D5 - turn Claude's reply text into a Python dict without ever crashing.

Lives in its own file so it can be tested on broken text with no API call:
    python parse_reply.py
"""

import json


def parse_reply(text):
    """Return the reply as a dict, or None if it is not valid JSON.

    Never raises. On failure it prints why, plus the raw text, so you can see
    exactly what the model said.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        # e.msg, e.lineno, e.colno are the same parts you read by hand in W02-D1.
        print(f"Could not parse the reply as JSON: {e.msg} "
              f"(line {e.lineno}, column {e.colno})")
        print("--- raw reply ---")
        print(repr(text))  # repr shows hidden things: quotes, \n, empty strings
        print("-----------------")
        return None

    # Valid JSON can still be the wrong shape, e.g. a list or a bare number.
    if not isinstance(data, dict):
        print(f"Reply is valid JSON but not an object: got {type(data).__name__}")
        print("--- raw reply ---")
        print(repr(text))
        print("-----------------")
        return None

    return data


# Running this file directly feeds it deliberately broken text.
# None of these may produce a traceback.
if __name__ == "__main__":
    broken_examples = [
        '{"colour": "black" "material": "leather"}',   # missing comma
        'Here is the JSON:\n{"colour": "black"}',      # preamble
        '```json\n{"colour": "black"}\n```',           # markdown code fence
        '{"colour": "black", "tags": ["tote", "le',    # cut off by max_tokens
        "",                                            # empty reply
        '["black", "leather"]',                        # valid JSON, wrong shape
    ]
    for text in broken_examples:
        print(f"\nINPUT: {text!r}")
        result = parse_reply(text)
        print(f"RESULT: {result}")

    print("\nAnd one good reply:")
    print(parse_reply('{"colour": "black", "tags": ["tote"]}'))
