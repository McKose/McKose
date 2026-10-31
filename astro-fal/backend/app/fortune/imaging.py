"""Server-side image gate before any vision tokens are spent.

- rejects non-images, oversized files and decompression bombs
- applies EXIF orientation, then strips all metadata (GPS etc., KVKK)
- downsizes to bound vision cost (tokens scale with resolution)
- rejects obviously unusable photos (too dark / blown out / blurry)

Quality thresholds are heuristics; calibrate on real uploads (see docs §5.3).
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SOURCE_PIXELS = 40_000_000
MAX_EDGE_PX = 1024
JPEG_QUALITY = 85
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

MIN_BRIGHTNESS = 35.0
MAX_BRIGHTNESS = 240.0
MIN_EDGE_VARIANCE = 25.0


class ImageRejected(ValueError):
    def __init__(self, code: str, message_tr: str) -> None:
        super().__init__(code)
        self.code = code
        self.message_tr = message_tr


@dataclass(frozen=True)
class PreparedImage:
    data: bytes
    width: int
    height: int
    brightness: float
    edge_variance: float


def prepare_image(raw: bytes) -> PreparedImage:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ImageRejected("too_large", "Fotoğraf çok büyük (en fazla 10 MB).")
    try:
        img = Image.open(io.BytesIO(raw))
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageRejected("not_an_image", "Dosya bir fotoğraf olarak okunamadı.") from exc
    if img.format not in ALLOWED_FORMATS:
        raise ImageRejected("unsupported_format", "Lütfen JPEG, PNG veya WEBP fotoğraf yükleyin.")
    # Size is known before decoding; refuse bombs without allocating them.
    if img.width * img.height > MAX_SOURCE_PIXELS:
        raise ImageRejected("too_many_pixels", "Fotoğraf çözünürlüğü çok yüksek.")

    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX), Image.Resampling.LANCZOS)

    gray = img.convert("L")
    brightness = ImageStat.Stat(gray).mean[0]
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # FIND_EDGES copies the 1-px frame from the source; crop it or flat images look "sharp".
    edge_var = ImageStat.Stat(edges.crop((2, 2, edges.width - 2, edges.height - 2))).var[0]
    if brightness < MIN_BRIGHTNESS:
        raise ImageRejected("too_dark", "Fotoğraf çok karanlık. Fincanı aydınlık bir yerde tekrar çek.")
    if brightness > MAX_BRIGHTNESS:
        raise ImageRejected("overexposed", "Fotoğraf çok parlak. Flaşı kapatıp tekrar dene.")
    if edge_var < MIN_EDGE_VARIANCE:
        raise ImageRejected("blurry", "Fotoğraf bulanık görünüyor. Telefonu sabit tutup tekrar çek.")

    out = io.BytesIO()
    # Re-encoding without exif= drops all metadata.
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return PreparedImage(out.getvalue(), img.width, img.height, round(brightness, 1), round(edge_var, 1))
