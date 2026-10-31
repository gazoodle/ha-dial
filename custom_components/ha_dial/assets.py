"""HA-rasterised Smooth text and icons, and the digit atlases shared by both renderers."""

import json
from functools import lru_cache
from math import ceil
from pathlib import Path

SUPERSAMPLE = 4
MASK_WIDTH, MASK_HEIGHT = 240, 120


@lru_cache(maxsize=512)
def _text_mask(text: str, size: int, colour: str, tracking: int = 0, weight: int = 0) -> dict:
    """Anti-aliased text with letter-spacing and weight; measured, so it is never clipped."""
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default(size=max(5, size) * SUPERSAMPLE)
    text = str(text)
    spacing = tracking * SUPERSAMPLE
    # Advances come from the whole string so that kerning survives letter-spacing.
    offsets = [font.getlength(text[:index]) + spacing * index for index in range(len(text))]
    width = ceil((offsets[-1] + font.getlength(text[-1]) if text else 0) + 2 * (weight + 1))
    ascent, descent = font.getmetrics()  # pyright: ignore[reportAttributeAccessIssue]  # Always a FreeType font here.
    height = ascent + descent + 2 * (weight + 1)
    image = Image.new("L", (max(1, width), max(1, height)))
    draw = ImageDraw.Draw(image)
    for offset, character in zip(offsets, text):
        draw.text((offset + weight + 1, weight + 1), character, font=font, fill=255, stroke_width=weight, stroke_fill=255)
    box = image.getbbox() or (0, 0, 1, 1)
    image = image.crop(box)
    scale = min(1, MASK_WIDTH * SUPERSAMPLE / image.width, MASK_HEIGHT * SUPERSAMPLE / image.height) / SUPERSAMPLE
    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    return {"op": "mask", "width": image.width, "height": image.height, "pixels": _pack(image.tobytes()), "colour": colour}


def _pack(values: bytes) -> str:
    """Two-bit coverage, rounded rather than floored so that fine strokes keep their weight."""
    return "".join(
        format(
            sum(
                ((values[start + offset] * 3 + 127) // 255) << (6 - offset * 2)
                for offset in range(min(4, len(values) - start))
            ),
            "02x",
        )
        for start in range(0, len(values), 4)
    )


@lru_cache(maxsize=16)
def _number_mask(size: int, raster: str = "smooth", extended: bool = False) -> dict:
    """A fixed-cell glyph atlas: each cell shares an advance and a baseline."""
    from PIL import Image, ImageDraw, ImageFont

    glyphs = "0123456789.-" if extended else "0123456789"
    if raster == "crisp":
        from .strokes import text_metrics, text_segments

        height = max(6, round(size * 0.9))
        sx, _ = text_metrics(height)
        width = round(4 * sx) + 3
        image = Image.new("1", (width, (height + 1) * len(glyphs)))
        draw = ImageDraw.Draw(image)
        for index, glyph in enumerate(glyphs):
            for x1, y1, x2, y2 in text_segments(glyph, height, 0):
                top = index * (height + 1)
                draw.line((x1 + 1, y1 + top, x2 + 1, y2 + top), fill=1)
        return {"width": width, "height": height + 1, "pixels": _pack(image.convert("L").tobytes())}

    font = ImageFont.load_default(size=size * 2)
    boxes = [font.getbbox(glyph) for glyph in glyphs]
    width = ceil(max(box[2] - box[0] for box in boxes))
    top, bottom = ceil(min(box[1] for box in boxes)), ceil(max(box[3] for box in boxes))
    height = bottom - top
    image = Image.new("L", (width, height * len(glyphs)))
    draw = ImageDraw.Draw(image)
    for digit, box in enumerate(boxes):
        draw.text(((width - (box[2] - box[0])) // 2 - box[0], digit * height - top), glyphs[digit], font=font, fill=255)
    cell_width, cell_height = min(64, ceil(width / 2)), min(64, ceil(height / 2))
    image = image.resize((cell_width, cell_height * len(glyphs)), Image.Resampling.LANCZOS)
    return {"width": cell_width, "height": cell_height, "pixels": _pack(image.tobytes())}


@lru_cache(maxsize=1)
def icon_names() -> dict:
    return json.loads((Path(__file__).with_name("resources") / "mdi.json").read_text())


def usable_icon(name, fallback: str) -> str:
    """An icon from outside this project, which may be custom or from a newer MDI than the bundled one."""
    return name if name in icon_names() else fallback


@lru_cache(maxsize=256)
def icon_mask(name: str, size: int, colour: str) -> dict:
    from PIL import Image, ImageDraw, ImageFont

    names = icon_names()
    if name not in names:
        raise ValueError(f"Unknown bundled MDI icon: {name}")
    font = ImageFont.truetype(str(Path(__file__).with_name("resources") / "mdi.ttf"), size * SUPERSAMPLE)
    image = Image.new("L", (size * SUPERSAMPLE, size * SUPERSAMPLE))
    glyph = chr(names[name])
    box = font.getbbox(glyph)
    ImageDraw.Draw(image).text(
        ((image.width - box[2] + box[0]) // 2 - box[0], (image.height - box[3] + box[1]) // 2 - box[1]),
        glyph,
        font=font,
        fill=255,
    )
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return {"op": "mask", "width": size, "height": size, "pixels": _pack(image.tobytes()), "colour": colour}
