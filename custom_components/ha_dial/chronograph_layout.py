"""Four Atlas chronographs compiled to display-pixel primitives in HA."""

from math import cos, pi, sin


def chronograph_layout(view, theme):
    elements, regions = [], []
    clock = view.get("_clock")
    primary, quiet = theme["primary"], theme["quiet"]

    def point(cx, cy, radius, angle):
        radians = (angle - 90) * pi / 180
        return [round(cx + radius * cos(radians)), round(cy + radius * sin(radians))]

    def path(points, colour):
        elements.append({"op": "polyline", "points": points, "stroke": colour})

    def circle(x, y, radius, stroke, fill=None):
        element = {"op": "circle", "x": x, "y": y, "r": radius, "stroke": stroke}
        if fill:
            element["fill"] = fill
        elements.append(element)

    def text(value, x, y, size=7, colour=None):
        elements.append(
            {
                "op": "mask",
                "x": x,
                "y": y,
                "text": str(value),
                "size": size,
                "colour": colour or theme["text"],
            }
        )

    def hand(x, y, radius, angle, colour, width=1):
        tip = point(x, y, radius, angle)
        if width == 1:
            path([[x, y], tip], colour)
            return
        from PIL import Image, ImageDraw

        image = Image.new("1", (240, 240))
        ImageDraw.Draw(image).line([(x, y), tuple(tip)], fill=1, width=width)
        points = []
        box = image.getbbox()
        if box:
            for row in range(box[1], box[3]):
                span = image.crop((box[0], row, box[2], row + 1)).getbbox()
                if span:
                    ends = [[box[0] + span[0], row], [box[0] + span[2] - 1, row]]
                    points.extend(ends if len(points) % 4 == 0 else reversed(ends))
        for start in range(0, len(points), 128):
            path(points[start : start + 128], colour)

    # Tick paths return to the perimeter before joining the next minute mark.
    for offset in range(0, 60, 20):
        points = []
        for index in range(offset, offset + 20):
            inner = point(120, 120, 98 if index % 5 else 94, index * 6)
            outer = point(120, 120, 103, index * 6)
            points.extend([outer, inner, outer])
        points.append(point(120, 120, 103, (offset + 20) * 6))
        path(points, quiet)
    circle(120, 120, 90, quiet, theme["surface"])
    circle(120, 120, 82, theme["grid"])
    if view["style"] != "CHR-WORLDTIMER":
        text(view.get("title", "HA DIAL").upper(), 120, 57, 7, theme["secondary"])
    if not clock:
        text("TIME UNAVAILABLE", 120, 118, 9)
        return elements, regions
    hour, minute, second = clock["hour"], clock["minute"], clock["second"]
    style = view["style"]

    def register(x, y, radius, value, total, caption):
        circle(x, y, radius, quiet, theme["bg"])
        ticks = []
        for angle in range(0, 361, 30):
            outer = point(x, y, radius - 2, angle)
            ticks.extend([outer, point(x, y, radius - 5, angle), outer])
        path(ticks, quiet)
        text(caption, x, y + radius // 2, 5, quiet)
        hand(x, y, radius - 6, value * 360 / total, theme["secondary"])
        circle(x, y, 2, primary, primary)

    if style in {"CHR-TRICOMPAX", "CHR-MOONPHASE"}:
        register(76, 119, 23, hour + minute / 60, 24, "24H")
        register(164, 119, 23, second, 60, "SEC")
        if style == "CHR-TRICOMPAX":
            register(120, 157, 23, clock["day"], 31, str(clock["day"]))
        else:
            circle(120, 157, 23, quiet, theme["bg"])
            phases = {
                "new_moon": 0,
                "waxing_crescent": 1,
                "first_quarter": 2,
                "waxing_gibbous": 3,
                "full_moon": 4,
                "waning_gibbous": 5,
                "last_quarter": 6,
                "waning_crescent": 7,
            }
            phase = phases.get(clock["moon"])
            if phase is None:
                text("NO MOON", 120, 153, 5, quiet)
                text("DATA", 120, 163, 5, quiet)
            else:
                # Orthographic illumination of a spherical moon; the HA phase selects the angle.
                phase_angle = phase * pi / 4
                points = []
                for y in range(-14, 15):
                    edge = (14**2 - y**2) ** 0.5
                    terminator = edge * cos(phase_angle)
                    left, right = (
                        (terminator, edge) if phase <= 4 else (-edge, -terminator)
                    )
                    if right - left >= 1:
                        ends = [
                            [round(120 + left), 157 + y],
                            [round(120 + right), 157 + y],
                        ]
                        points.extend(ends if len(points) % 4 == 0 else reversed(ends))
                if points:
                    path(points, theme["secondary"])
    elif style == "CHR-WORLDTIMER":
        zones = clock["zones"]
        for index, (name, value) in enumerate(zones):
            x, y = point(120, 120, 70, (index + 0.5) * 360 / len(zones))
            text(name[:8], x, y - 5, 7, primary if index == 0 else quiet)
            text(value, x, y + 5, 8)
        circle(120, 120, 43, quiet, theme["bg"])
        reserve = clock.get("reserve")
        if reserve is not None:
            elements.append(
                {
                    "op": "arc",
                    "x": 120,
                    "y": 120,
                    "r": 43,
                    "start": -110,
                    "end": round(-110 + 165 * reserve / 100),
                    "stroke": primary,
                    "width": 3,
                }
            )
        text(
            "RESERVE --" if reserve is None else f"RESERVE {reserve:g}%",
            120,
            91,
            5,
            quiet,
        )
        text(clock["zones"][0][1], 120, 148, 7, primary)
    else:
        path(
            [
                [58, 137],
                [88, 70],
                [113, 101],
                [137, 51],
                [182, 137],
                [144, 175],
                [83, 168],
                [58, 137],
            ],
            quiet,
        )
        register(82, 132, 26, hour % 12 + minute / 60, 12, "HOUR")
        register(158, 103, 31, minute + second / 60, 60, "MIN")
        register(139, 161, 17, second, 60, "SEC")
    if style != "CHR-SKELETON":
        hand(120, 120, 45, (hour % 12 + minute / 60) * 30, theme["text"], 3)
        hand(120, 120, 63, (minute + second / 60) * 6, theme["secondary"], 3)
        hand(120, 120, 74, second * 6, primary)
        circle(120, 120, 4, primary, primary)
    items = view.get("items", [])
    if items:
        selected = items[view.get("selected", 0) % len(items)]
        text(selected["label"], 120, 190, 8, primary)
        regions.append({"id": selected["id"], "x": 120, "y": 190, "r": 8})
    else:
        text(clock["date"], 120, 190, 7, quiet)
    return elements, regions
