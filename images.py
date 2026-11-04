"""Find an image's real type from its first bytes, not from its file extension.

Found in W04-D6: 7 photos named .PNG were really JPEGs, and the API rejected them
("specified using the image/png media type, but the image appears to be image/jpeg").
Every image format starts with a fixed "magic number", so the bytes can't lie.
"""

from pathlib import Path

# media type -> (file extension, test on the first 12 bytes)
SIGNATURES = {
    "image/jpeg": (".jpg", lambda b: b.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/gif": (".gif", lambda b: b[:6] in (b"GIF87a", b"GIF89a")),
    "image/webp": (".webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
}


def media_type_of(path):
    """'image/jpeg', 'image/png', 'image/gif', 'image/webp', or None if it's none of them."""
    with open(path, "rb") as f:
        head = f.read(12)
    for media_type, (_, matches) in SIGNATURES.items():
        if matches(head):
            return media_type
    return None


def extension_for(media_type):
    return SIGNATURES[media_type][0]


if __name__ == "__main__":
    import sys
    for name in sys.argv[1:]:
        print(f"{name}: {media_type_of(Path(name))}")
