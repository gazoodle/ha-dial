"""HA-rasterised text and fixed-cell digits shared by both renderers."""

from functools import lru_cache
from math import ceil


@lru_cache(maxsize=256)
def _text_mask(text: str, size: int, colour: str) -> dict:
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default(size=max(6, size * 2))
    text = str(text)[:16]
    box = font.getbbox(text)
    image = Image.new(
        "L", (max(1, ceil(box[2] - box[0])), max(1, ceil(box[3] - box[1])))
    )
    ImageDraw.Draw(image).text((-box[0], -box[1]), text, font=font, fill=255)
    width, height = max(1, (image.width + 1) // 2), max(1, (image.height + 1) // 2)
    scale = min(1, 120 / width, 32 / height)
    width, height = max(1, round(width * scale)), max(1, round(height * scale))
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    values = image.tobytes()
    pixels = _pack(values)
    return {
        "op": "mask",
        "width": width,
        "height": height,
        "pixels": pixels,
        "colour": colour,
    }


def _pack(values: bytes) -> str:
    return "".join(
        format(
            sum(
                (values[start + offset] >> 6) << (6 - offset * 2)
                for offset in range(min(4, len(values) - start))
            ),
            "02x",
        )
        for start in range(0, len(values), 4)
    )


@lru_cache(maxsize=8)
def _number_mask(size: int) -> dict:
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default(size=size * 2)
    boxes = [font.getbbox(str(digit)) for digit in range(10)]
    width = ceil(max(box[2] - box[0] for box in boxes))
    top, bottom = ceil(min(box[1] for box in boxes)), ceil(max(box[3] for box in boxes))
    height = bottom - top
    # Each cell has the same advance and baseline; the device never chooses font metrics.
    image = Image.new("L", (width, height * 10))
    draw = ImageDraw.Draw(image)
    for digit, box in enumerate(boxes):
        draw.text(
            ((width - (box[2] - box[0])) // 2 - box[0], digit * height - top),
            str(digit),
            font=font,
            fill=255,
        )
    cell_width, cell_height = min(32, ceil(width / 2)), min(32, ceil(height / 2))
    image = image.resize((cell_width, cell_height * 10), Image.Resampling.LANCZOS)
    return {
        "width": cell_width,
        "height": cell_height,
        "pixels": _pack(image.tobytes()),
    }
