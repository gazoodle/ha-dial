"""Four Atlas chronographs compiled to display-pixel primitives in HA."""

from math import cos, pi

from .canvas import Canvas, polar

MOON_PHASES = {
    "new_moon": 0, "waxing_crescent": 1, "first_quarter": 2, "waxing_gibbous": 3,
    "full_moon": 4, "waning_gibbous": 5, "last_quarter": 6, "waning_crescent": 7,
}


def chronograph_layout(c: Canvas, view: dict, o: dict) -> list[dict]:
    theme = c.theme
    clock = view.get("_clock")
    primary, quiet = theme["primary"], theme["quiet"]
    regions: list[dict] = []
    style = view["style"]
    surface = c.tint(0.55, theme["surface"])
    under = None if c.crisp else surface

    if o["tick-ring"]:
        c.ticks(120, 120, 119 - o["ring-inset"] - o["tick-inset"], o["tick-count"], o["tick-length"], quiet, 5, theme["secondary"], o["tick-length"] + 4)
    c.disc(120, 120, 90, theme["bg"] if c.crisp else surface, quiet)
    c.ring(120, 120, 82, theme["grid"], under=surface)
    if style != "CHR-WORLDTIMER":
        c.text(view.get("title", "HA DIAL").upper(), 120, 58, 7, theme["secondary"], under, tracking=2, weight=1, max_width=90)
    if not clock:
        c.text("TIME UNAVAILABLE", 120, 118, 9, theme["text"], under, tracking=1, max_width=140)
        return regions
    hour, minute, second = clock["hour"], clock["minute"], clock["second"]

    def hand(x, y, radius, angle, colour, width=1, ground=None):
        tip = polar(x, y, radius, angle)
        c.line(x, y, *tip, colour, width, ground if ground else under)

    def register(x, y, radius, value, total, caption):
        c.disc(x, y, radius, theme["bg"], quiet, under=surface)
        c.ticks(x, y, radius - 2, 12, 3, quiet, under=theme["bg"])
        c.text(caption, x, y + radius // 2, 6, quiet, None if c.crisp else theme["bg"], tracking=0)
        hand(x, y, radius - 6, value * 360 / total, theme["secondary"], ground=theme["bg"])
        c.disc(x, y, 2, primary, None, 1, None if c.crisp else theme["bg"])

    if style in {"CHR-TRICOMPAX", "CHR-MOONPHASE"}:
        register(76, 119, 23, hour + minute / 60, 24, "24H")
        register(164, 119, 23, second, 60, "SEC")
        if style == "CHR-TRICOMPAX":
            register(120, 157, 23, clock["day"], 31, str(clock["day"]))
        else:
            c.disc(120, 157, 23, theme["bg"], quiet, under=surface)
            phase = MOON_PHASES.get(clock["moon"])
            if phase is None:
                c.text("NO MOON", 120, 153, 6, quiet, None if c.crisp else theme["bg"], tracking=0)
                c.text("DATA", 120, 163, 6, quiet, None if c.crisp else theme["bg"], tracking=0)
            elif phase:
                # Orthographic illumination of a spherical moon; the HA phase selects the angle.
                terminator = cos(phase * pi / 4)
                left, right = [], []
                for row in range(-14, 15, 2):
                    edge = (14**2 - row**2) ** 0.5
                    span = (edge * terminator, edge) if phase <= 4 else (-edge, -edge * terminator)
                    left.append((120 + span[0], 157 + row))
                    right.append((120 + span[1], 157 + row))
                c.poly([*left, *reversed(right)], theme["secondary"], None if c.crisp else theme["bg"])
    elif style == "CHR-WORLDTIMER":
        zones = clock["zones"]
        for index, (name, value) in enumerate(zones):
            x, y = polar(120, 120, 66, (index + 0.5) * 360 / len(zones))
            c.text(name, x, y - 5, 6, primary if index == 0 else quiet, under, tracking=0, max_width=40)
            c.text(value, x, y + 5, 7, theme["text"], under, tracking=0)
        c.disc(120, 120, 38, theme["bg"], quiet, under=surface)
        reserve = clock.get("reserve")
        if reserve is not None:
            c.arc(120, 120, 38, -110, -110 + 165 * reserve / 100, primary, 3, under=surface)
        ground = None if c.crisp else theme["bg"]
        c.text("RESERVE --" if reserve is None else f"RESERVE {reserve:g}%", 120, 96, 6, quiet, ground, tracking=0, max_width=60)
        c.text(zones[0][1], 120, 146, 7, primary, ground, tracking=0)
    else:
        outline = [(58, 137), (88, 70), (113, 101), (137, 51), (182, 137), (144, 175), (83, 168)]
        c.path([*outline, outline[0]], quiet, under)
        register(82, 132, 26, hour % 12 + minute / 60, 12, "HOUR")
        register(158, 103, 31, minute + second / 60, 60, "MIN")
        register(139, 161, 17, second, 60, "SEC")

    if style != "CHR-SKELETON":
        width, length = o["hand-width"], o["hand-length"]
        ground = theme["bg"] if style == "CHR-WORLDTIMER" else surface
        hand(120, 120, length * 0.71, (hour % 12 + minute / 60) * 30, theme["text"], width, ground)
        hand(120, 120, length, (minute + second / 60) * 6, theme["secondary"], max(1, width - 1), ground)
        hand(120, 120, length + 11, second * 6, primary, 1, ground)
        c.disc(120, 120, 4, primary, None, 1, None if c.crisp else ground)
    items = view.get("items", [])
    if items:
        selected = items[view.get("selected", 0) % len(items)]
        c.text(selected["label"], 120, 190, 8, primary, tracking=1, max_width=110)
        regions.append({"id": selected["id"], "x": 120, "y": 190, "r": 8})
    else:
        c.text(clock["date"], 120, 190, 7, quiet, tracking=1, max_width=110)
    return regions
