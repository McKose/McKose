import io

import pytest
from PIL import Image, ImageDraw


def make_photo(seed: int = 0, size=(1600, 1200), brightness: int = 200, blank: bool = False, fmt: str = "JPEG") -> bytes:
    """Synthetic 'cup' photo: light background with dark blobs (enough edges to pass the blur gate)."""
    img = Image.new("RGB", size, (brightness, brightness - 10, brightness - 25))
    if not blank:
        d = ImageDraw.Draw(img)
        for i in range(60):
            x = (i * 97 + seed * 31) % size[0]
            y = (i * 53 + seed * 17) % size[1]
            r = 10 + (i * 7) % 40
            d.ellipse((x, y, x + r, y + r), fill=(60, 40, 25))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def photos() -> list[bytes]:
    return [make_photo(i) for i in range(3)]
