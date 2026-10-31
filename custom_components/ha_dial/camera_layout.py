"""Camera and photo faces. The picture is a frame the Dial blits; everything over it is primitives.

Detection boxes are absent on purpose: nothing generic in HA reports them, and an invented box on a
security camera is worse than none. A camera integration that burns boxes into its own image shows
them anyway. Detection state and confidence come only from the bound entity.
"""

from .canvas import Canvas, rounded
from .face_layout import FACES, _time


def _picture(c: Canvas, clock: dict, x, y, width, height, radius=8) -> dict | None:
    """The frame, or a plain panel saying honestly why there isn't one."""
    image = clock.get("image") or {"error": "NO SOURCE SET"}
    if "crc" in image:
        c.image(x, y, image)
    else:
        c.pill(x, y, width, height, c.theme["surface"], c.theme["quiet"], 1, radius=radius)
        c.text(image["error"], x, y, 8, c.theme["quiet"], c.theme["surface"], tracking=1, weight=1, max_width=width - 16)
    return image if "crc" in image else None


def _status_pill(c: Canvas, image: dict | None, y=24) -> None:
    text = f"CAMERA · {image['age']}" if image else "CAMERA"
    width = c.text_size(text, 7, 1, 1)[0] + 20
    fill = c.tint(0.13)
    c.pill(120, y, width, 18, None if c.crisp else fill, c.theme["primary"], 1)
    c.text(text, 120, y, 7, c.theme["secondary"], None if c.crisp else fill, tracking=1, weight=1)


def _warn(c: Canvas, image: dict | None, y, under=None) -> None:
    if image and image.get("error"):
        c.text(image["error"], 120, y, 7, c.theme["primary"], under, tracking=1, weight=1)


def cam_portal(c, clock, o):
    """A clean snapshot, its age, and up to two bound entities as direct actions."""
    image = _picture(c, clock, 120, 98, 144, 112, 16)
    _status_pill(c, image)
    if image:
        inset = rounded(120, 98, 128, 96, 10)
        c.path([*inset, inset[0]], c.theme["primary"], "#303030")
    _warn(c, image, 165)


def cam_cinema(c, clock, o):
    """A wide crop floating in the circle, with quiet status type."""
    image = _picture(c, clock, 120, 106, 164, 96, 5)
    c.text(clock.get("title", "CAMERA").upper(), 120, 44, o["label-size"] + 1, c.theme["secondary"], tracking=o["tracking"], weight=1, max_width=130)
    if image:
        c.text(image["age"], 120, 166, o["label-size"], c.theme["quiet"], tracking=o["tracking"], weight=1)
    _warn(c, image, 178)


def cam_radar(c, clock, o):
    """A tinted frame, targeting brackets, and what the bound detection entity actually reports."""
    theme = c.theme
    image = _picture(c, clock, 120, 106, 128, 128, 16)
    _status_pill(c, image)
    flat = []
    for x, y, dx, dy in ((60, 46, 1, 1), (180, 46, -1, 1), (60, 166, 1, -1), (180, 166, -1, -1)):
        flat.extend((x, y, x + 12 * dx, y, x, y, x, y + 12 * dy))
    c.lines(flat, theme["secondary"], "#303030")
    detection = clock.get("detection")
    text = "NO SENSOR" if detection is None else detection["text"]
    c.text(text, 120, 183, o["label-size"] + 1, theme["primary"] if detection and detection["active"] else theme["quiet"], tracking=min(o["tracking"], 1), weight=1, max_width=170)
    _warn(c, image, 150)


def wat_photos(c, clock, o):
    """A full-bleed photograph, with the time on its shaded lower edge."""
    image = clock.get("image") or {"error": "NO SOURCE SET"}
    if "crc" in image:
        c.image(120, 120, image, first=True)
    else:
        c.text(image["error"], 120, 90, 8, c.theme["quiet"], tracking=1, weight=1, max_width=150)
    under = "#060606"
    y = 158 + o["title-offset"]
    if c.crisp or image.get("mode") == "dither":
        # Thin strokes can't be read over a photograph, nor any text over a dither, so the time
        # gets a clear patch of its own.
        c.pill(112, y + 9, 128, o["value-size"] + 24, c.theme["bg"], None, radius=6)
    c.text(_time(clock), 57, y, o["value-size"] - 3, "#ffffff", under if not c.crisp else None, align="start", tracking=0, weight=1)
    weather = clock.get("weather")
    detail = f"{clock['date']} · {weather['temperature']}" if weather else clock["date"]
    c.text(detail, 59, y + 21, o["label-size"] + 1, "#ffffff", under if not c.crisp else None, align="start", tracking=1, weight=1, max_width=130)


FACES.update({"CAM-PORTAL": cam_portal, "CAM-CINEMA": cam_cinema, "CAM-RADAR": cam_radar, "WAT-PHOTOS": wat_photos})
