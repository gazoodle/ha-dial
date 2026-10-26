"""Render a compact Casa Mia-style pill for the dial."""

from __future__ import annotations

from functools import lru_cache
from math import ceil

from PIL import Image, ImageDraw, ImageFont

HEIGHT = 22
MAX_WIDTH = 150
SCALE = 4
PADDING = 9
FONT_SIZE = 10
TRACKING = 0.04


@lru_cache(maxsize=32)
def render_pill(label: str) -> dict[str, int | str]:
    """Return a four-bit antialiased mask ready for the device."""
    text = " ".join(label.upper().split()) or "LIGHT"
    font = ImageFont.load_default(size=FONT_SIZE * SCALE)
    spacing = FONT_SIZE * SCALE * TRACKING

    def text_width(value: str) -> float:
        return sum(font.getlength(char) for char in value) + spacing * max(0, len(value) - 1)

    while text_width(text) > (MAX_WIDTH - 2 * PADDING) * SCALE and len(text) > 1:
        text = text[:-1].rstrip()
    if text != " ".join(label.upper().split()):
        text = text[:-3].rstrip() + "..." if len(text) > 3 else text

    width = min(MAX_WIDTH, max(HEIGHT, ceil(text_width(text) / SCALE) + 2 * PADDING))
    image = Image.new("L", (width * SCALE, HEIGHT * SCALE))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (0, 0, width * SCALE - 1, HEIGHT * SCALE - 1),
        radius=HEIGHT * SCALE // 2,
        fill=round(255 * 0.14),
        outline=255,
        width=SCALE,
    )

    x = (width * SCALE - text_width(text)) / 2
    for char in text:
        box = font.getbbox(char)
        y = (HEIGHT * SCALE - (box[3] - box[1])) / 2 - box[1]
        draw.text((round(x), round(y)), char, font=font, fill=255)
        x += font.getlength(char) + spacing

    image = image.resize((width, HEIGHT), Image.Resampling.LANCZOS)
    pixels = "".join(format(round(value * 15 / 255), "x") for value in image.tobytes())
    return {"width": width, "height": HEIGHT, "pixels": pixels}
