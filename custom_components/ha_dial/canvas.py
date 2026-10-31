"""Layouts draw on this; it resolves one design vocabulary to Crisp or Smooth scene elements.

Crisp means line-step strokes and hard fills. Smooth means coverage blended against a declared
colour, because the Dial has no framebuffer to read back from.
"""

from itertools import pairwise
from math import atan2, cos, pi, sin

from .assets import _number_mask, _text_mask, icon_mask
from .strokes import icon_segments, text_segments, text_width

MAX_SEGMENTS = 256


def polar(cx, cy, radius, degrees):
    """Clockwise degrees from 12 o'clock to display coordinates."""
    angle = (degrees - 90) * pi / 180
    return cx + cos(angle) * radius, cy + sin(angle) * radius


def mix(colour, base, amount):
    """Flatten translucency in HA: the scene only ever carries opaque colours."""
    front = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    back = [int(base[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(b + (f - b) * amount):02x}" for f, b in zip(front, back))


def _quarter(value):
    return max(0, min(959, round(value * 4)))


def _pixel(value):
    return max(0, min(239, round(value)))


class Canvas:
    def __init__(self, theme: dict, crisp: bool):
        self.theme = theme
        self.crisp = crisp
        self.elements: list[dict] = []

    def tint(self, amount: float, colour: str | None = None) -> str:
        return mix(colour or self.theme["primary"], self.theme["bg"], amount)

    def _soft(self, under):
        return {} if self.crisp else {"background": under or self.theme["bg"]}

    def ring(self, x, y, r, colour, width=1, under=None):
        element = {"op": "circle", "x": round(x), "y": round(y), "r": round(r), "stroke": colour}
        if self.crisp and width == 1:
            self.elements.append(element)  # Midpoint circle: the line-step character itself.
            return
        self.elements.append({**element, "width": width, "solid": True, **self._soft(under)})

    def disc(self, x, y, r, fill, stroke=None, width=1, under=None):
        element = {"op": "circle", "x": round(x), "y": round(y), "r": round(r), "fill": fill}
        if stroke:
            element.update(stroke=stroke, width=width)
        if self.crisp and width == 1:
            self.elements.append(element)
            return
        self.elements.append({**element, "solid": True, **self._soft(under)})

    def arc(self, x, y, r, start, end, colour, width=1, cap=False, under=None):
        element = {"op": "arc", "x": round(x), "y": round(y), "r": round(r), "start": round(start), "end": round(end), "stroke": colour, "width": width}
        if self.crisp and width == 1:
            self.elements.append(element)
            return
        self.elements.append({**element, "solid": True, "cap": cap, **self._soft(under)})

    def gauge(self, x, y, r, start, end, value, colour, width, fill=None, minimum=0, maximum=100, cap=False, under=None):
        """A firmware-updated arc, so rotary feedback stays local and immediate."""
        element = {
            "op": "gauge", "x": round(x), "y": round(y), "r": round(r), "start": round(start), "end": round(end),
            "value": max(0, min(100, round(value))), "stroke": colour, "fill": fill or colour,
            "minimum": minimum, "maximum": maximum, "width": width,
        }
        if self.crisp and width == 1:
            self.elements.append(element)
            return
        self.elements.append({**element, "solid": True, "cap": cap, **self._soft(under)})

    def line(self, x1, y1, x2, y2, colour, width=1, under=None):
        if width <= 1:
            self.elements.append({"op": "line", "x1": _pixel(x1), "y1": _pixel(y1), "x2": _pixel(x2), "y2": _pixel(y2), "stroke": colour, **self._soft(under)})
            return
        self.poly(capsule(x1, y1, x2, y2, width), colour, under)

    def lines(self, flat, colour, under=None):
        """Many strokes in one element; this is what makes fans and moiré affordable."""
        flat = [_pixel(value) for value in flat]
        for start in range(0, len(flat), MAX_SEGMENTS * 4):
            self.elements.append({"op": "segments", "lines": flat[start : start + MAX_SEGMENTS * 4], "stroke": colour, **self._soft(under)})

    def path(self, points, colour, under=None):
        self.elements.append({"op": "polyline", "points": [[_pixel(x), _pixel(y)] for x, y in points[:128]], "stroke": colour, **self._soft(under)})

    def poly(self, points, fill, under=None):
        self.elements.append({"op": "polygon", "points": [[_quarter(x), _quarter(y)] for x, y in points[:128]], "fill": fill, **self._soft(under)})

    def hatch(self, points, colour, spacing=3, under=None):
        """Even-odd horizontal hatching clipped to a polygon, for Crisp's tinted surfaces."""
        low, high = min(y for _, y in points), max(y for _, y in points)
        flat = []
        y = round(low) + 1
        while y < high:
            crossings = sorted(
                a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                for a, b in pairwise([*points, points[0]])
                if (a[1] <= y) != (b[1] <= y)
            )
            for left, right in zip(crossings[::2], crossings[1::2]):
                flat.extend((left + 2, y, right - 2, y))
            y += spacing
        if flat:
            self.lines(flat, colour, under)

    def surface(self, points, fill, stroke, under=None, hatch=None):
        """A filled shape in Smooth; an outline with optional hatching in Crisp."""
        if self.crisp:
            if hatch:
                self.hatch(points, hatch)
            self.path([*points, points[0]], stroke)
            return
        self.poly(points, fill, under)
        self.path([*points, points[0]], stroke, fill)

    def pill(self, x, y, width, height, fill, stroke=None, border=1, radius=None, under=None):
        """Rounded rectangle, centred; nested polygons give it an anti-aliased border."""
        radius = height / 2 if radius is None else min(radius, height / 2, width / 2)
        if stroke and not self.crisp:
            self.poly(rounded(x, y, width, height, radius), stroke, under)
            self.poly(rounded(x, y, width - 2 * border, height - 2 * border, max(0, radius - border)), fill, stroke)
            return
        if fill:
            self.poly(rounded(x, y, width, height, radius), fill, under)
        if stroke:
            for inset in range(border):
                outline = rounded(x, y, width - 2 * inset, height - 2 * inset, max(0, radius - inset))
                self.path([*outline, outline[0]], stroke)

    def ticks(self, cx, cy, radius, count, length, colour, major=0, major_colour=None, major_length=None, start=0, sweep=360, under=None):
        minor, strong = [], []
        steps = count if sweep >= 360 else max(1, count - 1)
        for index in range(count):
            angle = start + index * sweep / steps
            is_major = bool(major) and index % major == 0
            target = strong if is_major else minor
            inner = radius - (major_length if is_major and major_length else length)
            target.extend((*polar(cx, cy, inner, angle), *polar(cx, cy, radius, angle)))
        if minor:
            self.lines(minor, colour, under)
        if strong:
            self.lines(strong, major_colour or colour, under)

    def text_size(self, value, size, tracking=1, weight=0):
        if self.crisp:
            return text_width(str(value), _cap_height(size), tracking), _cap_height(size)
        mask = _text_mask(str(value), size, "#ffffff", tracking, weight)
        return mask["width"], mask["height"]

    def _fit(self, value, size, tracking, weight, max_width):
        """Shrink, then elide with two dots. Text is never silently cut."""
        value = str(value)
        if not max_width or not value:
            return value, size
        floor = min(size, 6)
        while size > floor and self.text_size(value, size, tracking, weight)[0] > max_width:
            size -= 1
        while len(value) > 1 and self.text_size(value, size, tracking, weight)[0] > max_width:
            value = value[:-3].rstrip() + ".." if len(value) > 3 else value[:-1]
        return value, size

    def text(self, value, x, y, size, colour, under=None, align="middle", tracking=1, weight=0, max_width=None):
        """Text centred vertically on y, aligned horizontally about x."""
        value, size = self._fit(value, size, tracking, weight, max_width)
        if not str(value).strip():
            return
        if self.crisp:
            height = _cap_height(size)
            width = text_width(value, height, tracking)
            left = x - width / 2 if align == "middle" else x - width if align == "end" else x
            top = round(y - height / 2)
            flat = []
            for x1, y1, x2, y2 in text_segments(value, height, tracking):
                flat.extend((round(left) + x1, top + y1, round(left) + x2, top + y2))
            self.lines(flat, colour)
            return
        mask = _text_mask(value, size, colour, tracking, weight)
        centre = x if align == "middle" else x - mask["width"] / 2 if align == "end" else x + mask["width"] / 2
        self.elements.append({**mask, "x": _pixel(centre), "y": _pixel(y), "background": under or self.theme["bg"]})

    def icon(self, name, x, y, size, colour, under=None):
        if self.crisp:
            flat = []
            left, top = round(x - size / 2), round(y - size / 2)
            for x1, y1, x2, y2 in icon_segments(name, size):
                flat.extend((left + x1, top + y1, left + x2, top + y2))
            if flat:
                self.lines(flat, colour)
            return
        self.elements.append({**icon_mask(name, size, colour), "x": _pixel(x), "y": _pixel(y), "background": under or self.theme["bg"]})

    def number_cell(self, size) -> int:
        return _number_mask(size, "crisp" if self.crisp else "smooth", True)["width"]

    def number(self, value, x, y, size, colour, stroke, extended=False, precision=0, under=None):
        """A digit atlas the firmware reuses for immediate local rotary feedback."""
        element = {
            "op": "number", "x": _pixel(x), "y": _pixel(y), "value": value, "colour": colour, "stroke": stroke,
            "background": under or self.theme["bg"], **_number_mask(size, "crisp" if self.crisp else "smooth", extended),
        }
        if extended:
            element.update(precision=precision, characters="0123456789.-")
        self.elements.append(element)


def _cap_height(size):
    """Crisp's caps stay open enough for the line-step to read, even when small."""
    return max(6, round(size * 0.9))


def capsule(x1, y1, x2, y2, width):
    """A thick line with round ends as one polygon."""
    angle = atan2(y2 - y1, x2 - x1)
    radius = width / 2
    points = []
    for cx, cy, start in ((x2, y2, angle - pi / 2), (x1, y1, angle + pi / 2)):
        points.extend((cx + radius * cos(start + step * pi / 4), cy + radius * sin(start + step * pi / 4)) for step in range(5))
    return points


def rounded(x, y, width, height, radius):
    """A rounded rectangle centred on x, y, as polygon points."""
    left, right, top, bottom = x - width / 2, x + width / 2, y - height / 2, y + height / 2
    if radius <= 0:
        return [(left, top), (right, top), (right, bottom), (left, bottom)]
    corners = ((right - radius, top + radius, -90), (right - radius, bottom - radius, 0), (left + radius, bottom - radius, 90), (left + radius, top + radius, 180))
    return [
        (cx + radius * cos((start + step * 22.5) * pi / 180), cy + radius * sin((start + step * 22.5) * pi / 180))
        for cx, cy, start in corners
        for step in range(5)
    ]
