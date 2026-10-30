"""HA-rasterised text and fixed-cell digits shared by both renderers."""

import json
from functools import lru_cache
from math import ceil
from pathlib import Path


@lru_cache(maxsize=256)
def _text_mask(text: str, size: int, colour: str, raster: str = "smooth") -> dict:
    from PIL import Image, ImageDraw, ImageFont

    if raster == "crisp":
        font = ImageFont.load_default(size=max(6, size))
        text = str(text)[:16]
        box = font.getbbox(text)
        image = Image.new("1", (max(1, box[2] - box[0]), max(1, box[3] - box[1])))
        ImageDraw.Draw(image).text((-box[0], -box[1]), text, font=font, fill=1)
        scale = min(1, 120 / image.width, 32 / image.height)
        if scale < 1:
            image = image.resize(
                (
                    max(1, round(image.width * scale)),
                    max(1, round(image.height * scale)),
                ),
                Image.Resampling.NEAREST,
            )
        return {
            "op": "mask",
            "width": image.width,
            "height": image.height,
            "pixels": _pack(image.convert("L").tobytes()),
            "colour": colour,
        }

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
    pixels = _pack(image.tobytes())
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
def _number_mask(size: int, raster: str = "smooth", extended: bool = False) -> dict:
    from PIL import Image, ImageDraw, ImageFont

    factor = 1 if raster == "crisp" else 2
    font = ImageFont.load_default(size=size * factor)
    glyphs = "0123456789.-" if extended else "0123456789"
    boxes = [font.getbbox(glyph) for glyph in glyphs]
    width = ceil(max(box[2] - box[0] for box in boxes))
    top, bottom = ceil(min(box[1] for box in boxes)), ceil(max(box[3] for box in boxes))
    height = bottom - top
    # Each cell has the same advance and baseline; the device never chooses font metrics.
    image = Image.new("1" if raster == "crisp" else "L", (width, height * len(glyphs)))
    draw = ImageDraw.Draw(image)
    for digit, box in enumerate(boxes):
        draw.text(
            ((width - (box[2] - box[0])) // 2 - box[0], digit * height - top),
            glyphs[digit],
            font=font,
            fill=1 if raster == "crisp" else 255,
        )
    cell_width, cell_height = (
        min(32, ceil(width / factor)),
        min(32, ceil(height / factor)),
    )
    image = image.resize(
        (cell_width, cell_height * len(glyphs)),
        Image.Resampling.NEAREST if raster == "crisp" else Image.Resampling.LANCZOS,
    )
    return {
        "width": cell_width,
        "height": cell_height,
        "pixels": _pack(
            image.convert("L").tobytes() if raster == "crisp" else image.tobytes()
        ),
    }


@lru_cache(maxsize=1)
def icon_names() -> dict:
    return json.loads((Path(__file__).with_name("resources") / "mdi.json").read_text())


@lru_cache(maxsize=256)
def icon_mask(name: str, size: int, colour: str, raster: str = "smooth") -> dict:
    from PIL import Image, ImageDraw, ImageFont

    names = icon_names()
    if name not in names:
        raise ValueError(f"Unknown bundled MDI icon: {name}")
    factor = 1 if raster == "crisp" else 4
    font = ImageFont.truetype(
        str(Path(__file__).with_name("resources") / "mdi.ttf"), size * factor
    )
    image = Image.new("1" if raster == "crisp" else "L", (size * factor, size * factor))
    glyph = chr(names[name])
    box = font.getbbox(glyph)
    ImageDraw.Draw(image).text(
        (
            (image.width - box[2] + box[0]) // 2 - box[0],
            (image.height - box[3] + box[1]) // 2 - box[1],
        ),
        glyph,
        font=font,
        fill=1 if raster == "crisp" else 255,
    )
    if raster != "crisp":
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    values = image.convert("L").tobytes()
    return {
        "op": "mask",
        "width": size,
        "height": size,
        "pixels": _pack(values),
        "colour": colour,
    }
