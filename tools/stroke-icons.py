"""Regenerate resources/stroke_icons.json from the Atlas's stroke icons; run after editing icons.js."""

import json
import re
from itertools import pairwise
from math import acos, ceil, copysign, cos, pi, radians, sin, sqrt
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "tools/ux-gallery/icons.js").read_text()
TOKEN = re.compile(r"[A-Za-z]|-?(?:\d+\.\d*|\.\d+|\d+)")


def curve(points, count=6):
    """Sample a quadratic or cubic Bezier given its control points, excluding the start."""
    result = []
    for step in range(1, count + 1):
        t, row = step / count, list(points)
        while len(row) > 1:
            row = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in pairwise(row)]
        result.append(row[0])
    return result


def arc(start, rx, ry, rotation, large, sweep, end):
    """SVG endpoint arc to polyline, per the SVG implementation notes."""
    phi = radians(rotation)
    dx, dy = (start[0] - end[0]) / 2, (start[1] - end[1]) / 2
    x1, y1 = cos(phi) * dx + sin(phi) * dy, -sin(phi) * dx + cos(phi) * dy
    scale = x1**2 / rx**2 + y1**2 / ry**2
    if scale > 1:
        rx, ry = rx * sqrt(scale), ry * sqrt(scale)
    top = max(0, rx**2 * ry**2 - rx**2 * y1**2 - ry**2 * x1**2)
    factor = sqrt(top / (rx**2 * y1**2 + ry**2 * x1**2)) * (-1 if large == sweep else 1)
    cx1, cy1 = factor * rx * y1 / ry, -factor * ry * x1 / rx
    cx = cos(phi) * cx1 - sin(phi) * cy1 + (start[0] + end[0]) / 2
    cy = sin(phi) * cx1 + cos(phi) * cy1 + (start[1] + end[1]) / 2

    def angle(ux, uy, vx, vy):
        length = sqrt(ux**2 + uy**2) * sqrt(vx**2 + vy**2)
        return copysign(acos(max(-1, min(1, (ux * vx + uy * vy) / length))), ux * vy - uy * vx)

    theta = angle(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    delta = angle((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not sweep and delta > 0:
        delta -= 2 * pi
    elif sweep and delta < 0:
        delta += 2 * pi
    count = max(3, ceil(abs(delta) / (pi / 6)))
    return [
        (
            cx + rx * cos(theta + delta * n / count) * cos(phi) - ry * sin(theta + delta * n / count) * sin(phi),
            cy + rx * cos(theta + delta * n / count) * sin(phi) + ry * sin(theta + delta * n / count) * cos(phi),
        )
        for n in range(1, count + 1)
    ]


def flags(data):
    """Arc flags may be written without separators, so split them out before tokenising."""
    return re.sub(
        r"([aA])((?:[^a-zA-Z]*))",
        lambda m: m.group(1) + re.sub(r"(-?[\d.]+[ ,]+-?[\d.]+[ ,]+-?[\d.]+[ ,]+)([01])[ ,]*([01])[ ,]*", r"\1\2 \3 ", m.group(2)),
        data,
    )


def parse(data):
    tokens = TOKEN.findall(flags(data))
    paths, path, x, y, index, command, control = [], [], 0.0, 0.0, 0, "", None

    def take(count):
        nonlocal index
        values = [float(tokens[index + n]) for n in range(count)]
        index += count
        return values

    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        relative = command.islower()
        kind = command.lower()
        base = (x, y) if relative else (0.0, 0.0)
        if kind == "z":
            if path:
                path.append(path[0])
                x, y = path[0]
            continue
        if kind == "m":
            a, b = take(2)
            x, y = a + base[0], b + base[1]
            if len(path) > 1:
                paths.append(path)
            path = [(x, y)]
            command = "l" if relative else "L"
        elif kind == "l":
            a, b = take(2)
            x, y = a + base[0], b + base[1]
            path.append((x, y))
        elif kind == "h":
            x = take(1)[0] + (x if relative else 0)
            path.append((x, y))
        elif kind == "v":
            y = take(1)[0] + (y if relative else 0)
            path.append((x, y))
        elif kind in "cs":
            values = take(6 if kind == "c" else 4)
            points = [(values[n] + base[0], values[n + 1] + base[1]) for n in range(0, len(values), 2)]
            first = points[0] if kind == "c" else (2 * x - control[0], 2 * y - control[1]) if control else (x, y)
            rest = points[1:] if kind == "c" else points
            path.extend(curve([(x, y), first, *rest]))
            control = rest[0]
            x, y = rest[1]
            continue
        elif kind == "q":
            values = take(4)
            points = [(values[n] + base[0], values[n + 1] + base[1]) for n in (0, 2)]
            path.extend(curve([(x, y), *points]))
            x, y = points[1]
        elif kind == "a":
            rx, ry, rotation, large, sweep, a, b = take(7)
            end = (a + base[0], b + base[1])
            path.extend(arc((x, y), rx, ry, rotation, large, sweep, end))
            x, y = end
        else:
            raise ValueError(f"Unsupported path command {command} in {data}")
        control = None
    if len(path) > 1:
        paths.append(path)
    return paths


def ring(cx, cy, r, count=12):
    return [(cx + r * cos(2 * pi * n / count), cy + r * sin(2 * pi * n / count)) for n in range(count + 1)]


def box(x, y, w, h, r):
    """Rounded rectangle as one closed polyline."""
    steps = [(x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)]
    points = []
    for cx, cy, start in steps:
        points.extend((cx + r * cos(radians(start + n * 30)), cy + r * sin(radians(start + n * 30))) for n in range(4))
    return [*points, points[0]]


attribute = lambda text, name: float(re.search(rf'{name}="(-?[\d.]+)"', text).group(1)) if re.search(rf'{name}="', text) else 0.0
icons = {}
for name, body in re.findall(r"^\s*(\w+): `(.*)`,$", source, re.MULTILINE):
    paths = []
    for tag, attributes in re.findall(r"<(path|rect|circle)\s([^>]*)/>", body):
        if tag == "path":
            paths.extend(parse(re.search(r'd="([^"]*)"', attributes).group(1)))
        elif tag == "circle":
            paths.append(ring(attribute(attributes, "cx"), attribute(attributes, "cy"), attribute(attributes, "r")))
        else:
            paths.append(box(*(attribute(attributes, key) for key in ("x", "y", "width", "height", "rx"))))
    icons[name] = [[[round(a * 4) / 4, round(b * 4) / 4] for a, b in path] for path in paths]
(root / "custom_components/ha_dial/resources/stroke_icons.json").write_text(json.dumps(icons, separators=(",", ":")))
print(len(icons), "icons")
