"""Snake navigation geometry: rows joined by U-turns, and where the icons sit along them.

Everything is measured by distance along the path, so both ways of placing icons, the scrolling
window and the line between icons share one model. Rows run along u and stack across v; the twist
then rotates the whole snake as one, and only the icons and label stay upright.
"""

from dataclasses import dataclass, field
from math import cos, hypot, pi, radians, sin

# Scenes allow 64 elements. A one-pixel line shares one element per colour, but each thick stroke is
# its own, so a thick double line can afford fewer icons alongside it.
MAX_ICONS = 12
MAX_ICONS_THICK_DOUBLE = 9
# How far the line runs towards an icon scrolled out of view, so it's plain there is more.
TAIL = 30
# The space above the label and below the settings cog, and the display inside its outer ring.
MIDDLE = 98
AREA_WIDTH = 224
AREA_HEIGHT = 136
OUTER_RADIUS = 113
MIN_SCALE = 0.3


@dataclass
class Snake:
    icons: list[tuple] = field(default_factory=list)  # index, x, y
    lines: list[tuple] = field(default_factory=list)  # x1, y1, x2, y2, travelled
    arcs: list[tuple] = field(default_factory=list)  # x, y, r, start, end, travelled


class _Path:
    def __init__(self, rows: int, length: float, extension: float, turn: float):
        half, reach = length / 2, length / 2 + extension
        self.turn_length = pi * turn
        self.pieces = []  # (length, kind, data), consecutive along the path.
        for row in range(rows):
            v = (row - (rows - 1) / 2) * 2 * turn
            forward = row % 2 == 0
            entry = -half if row == 0 else (-reach if forward else reach)
            end = (half if row == rows - 1 else reach) * (1 if forward else -1)
            self.pieces.append((abs(end - entry), "line", (entry, end, v)))
            if row < rows - 1:
                self.pieces.append((self.turn_length, "turn", (end, v + turn, turn, forward)))

    @property
    def total(self) -> float:
        return sum(piece[0] for piece in self.pieces)

    def row_at(self, distance: float) -> int:
        """A turn belongs to the row it leaves."""
        for index, (length, _, _) in enumerate(self.pieces):
            if distance <= length:
                return index // 2
            distance -= length
        return (len(self.pieces) - 1) // 2

    def at(self, distance: float) -> tuple[float, float]:
        for length, kind, data in self.pieces:
            if distance <= length:
                return _point(kind, data, distance / length if length else 0)
            distance -= length
        length, kind, data = self.pieces[-1]
        return _point(kind, data, 1)

    def slices(self, first: float, last: float):
        """The parts of each piece between two distances along the path, as fractions of the piece."""
        at = 0.0
        for length, kind, data in self.pieces:
            low, high = max(first, at), min(last, at + length)
            if high > low and length:
                yield kind, data, (low - at) / length, (high - at) / length
            at += length


def _point(kind, data, fraction) -> tuple[float, float]:
    if kind == "line":
        entry, end, v = data
        return entry + (end - entry) * fraction, v
    u, v, turn, right = data
    angle = pi * fraction
    return u + (turn * sin(angle) if right else -turn * sin(angle)), v - turn * cos(angle)


def _placed(count: int, o: dict, scale: float) -> tuple[_Path, list[float]]:
    """The path this many icons need, and each icon's distance along it."""
    length, extension, turn = o["snake-row-length"] * scale, o["snake-extension"] * scale, o["snake-turn"] * scale
    if o["snake-placement"] == "along path":
        spacing = o["snake-spacing"] * scale
        rows = 1
        while _Path(rows, length, extension, turn).total < (count - 1) * spacing:
            rows += 1
        return _Path(rows, length, extension, turn), [n * spacing for n in range(count)]

    per_row = o["snake-per-row"]
    rows = (count + per_row - 1) // per_row
    path = _Path(rows, length, extension, turn)
    stops, at = [], 0.0
    for row in range(rows):
        lead = extension if row else 0
        stops += [at + lead + n * length / (per_row - 1) for n in range(min(per_row, count - len(stops)))]
        at += path.pieces[row * 2][0] + path.turn_length
    return path, stops


def _window(path: _Path, stops: list[float], focus: int, o: dict, rest: int) -> range:
    """Whole rows around the selection, so scrolling never breaks the snake's reading order."""
    rows = path.row_at(path.total) + 1
    pitch = 2 * o["snake-turn"]
    shown = max(1, int((AREA_HEIGHT - 2 * rest) / pitch) + 1)
    first = max(0, min(path.row_at(stops[focus]) - shown // 2, rows - shown))
    visible = [n for n, stop in enumerate(stops) if first <= path.row_at(stop) < first + shown]

    limit = MAX_ICONS_THICK_DOUBLE if o["snake-edge"] == "double" and o["snake-width"] > 1 else MAX_ICONS
    low, high = visible[0], visible[-1] + 1
    while high - low > limit:
        if focus - low > high - 1 - focus:
            low += 1
        else:
            high -= 1
    return range(low, high)


def _strokes(path, stops, window, selected, radius, o, rotate) -> Snake:
    """The line between icons, stopping short of each so nothing has to blend through a ring."""
    snake = Snake()
    twist = o["snake-twist"]
    clearance = o["snake-clearance"]
    offsets = (0,) if o["snake-edge"] == "single" else (-o["snake-gap"], o["snake-gap"])
    for n in range(max(window.start - 1, 0), min(window.stop, len(stops) - 1)):
        first, last = stops[n] + radius(n) + clearance, stops[n + 1] - radius(n + 1) - clearance
        if n < window.start:
            first = max(first, last - TAIL)
        if n + 1 >= window.stop:
            last = min(last, first + TAIL)
        for kind, data, start, end in path.slices(first, last):
            if kind == "line":
                entry, finish, v = data
                a, b = entry + (finish - entry) * start, entry + (finish - entry) * end
                snake.lines += [(*rotate(a, v + edge), *rotate(b, v + edge), n < selected) for edge in offsets]
                continue
            u, v, turn, right = data
            low, high = (180 * start, 180 * end) if right else (360 - 180 * end, 360 - 180 * start)
            low, high = low + twist, high + twist
            # Firmware rejects a scene whose arc leaves -360 to 360, and the twist can push one past it.
            if high > 360:
                low, high = low - 360, high - 360
            if round(high) > round(low):
                snake.arcs += [(*rotate(u, v), max(1, turn + edge), low, high, n < selected) for edge in offsets]
    return snake


def _extent(snake, window, stops, path, radius, rotate, margin) -> list[tuple]:
    """Every point the snake must keep on screen, with how much it reaches beyond that point."""
    points = [(*rotate(*path.at(stops[n])), radius(n)) for n in window]
    points += [(x, y, margin) for x1, y1, x2, y2, _ in snake.lines for x, y in ((x1, y1), (x2, y2))]
    for x, y, r, start, end, _ in snake.arcs:
        points.append((x, y, 0))  # Firmware also needs the centre on screen.
        points += [
            (x + sin(radians(angle)) * r, y - cos(radians(angle)) * r, margin)
            for angle in (start + (end - start) * step / 8 for step in range(9))
        ]
    return points


def arrange(count: int, selected: int, o: dict, rest: int) -> Snake:
    """Lay out the snake, centred on its real shape and shrunk only if it can't otherwise fit."""
    if not count:
        return Snake()
    focus = selected if selected < count else 0
    radius = lambda n: o["highlight-radius"] if n == selected else rest
    twist = radians(o["snake-twist"])
    middle = MIDDLE + o["snake-position"]
    outer = OUTER_RADIUS - o["ring-inset"]
    margin = (0 if o["snake-edge"] == "single" else o["snake-gap"]) + o["snake-width"] / 2

    def rotated(u, v):
        return u * cos(twist) - v * sin(twist), u * sin(twist) + v * cos(twist)

    scale = 1.0
    while True:
        path, stops = _placed(count, o, scale)
        window = _window(path, stops, focus, o, rest)
        points = _extent(_strokes(path, stops, window, selected, radius, o, rotated), window, stops, path, radius, rotated, margin)
        left, right = min(x - r for x, _, r in points), max(x + r for x, _, r in points)
        top, bottom = min(y - r for _, y, r in points), max(y + r for _, y, r in points)
        # Whole pixels, so a twist-free snake keeps its rows and turns on the pixel grid.
        dx, dy = round(120 - (left + right) / 2), round(middle - (top + bottom) / 2)
        far = max(hypot(x + dx - 120, y + dy - 120) + r for x, y, r in points)
        fit = min(1, AREA_WIDTH / (right - left), AREA_HEIGHT / (bottom - top), outer / far)
        if fit >= 1 or scale <= MIN_SCALE:
            break
        scale = max(MIN_SCALE, scale * fit)

    def place(u, v):
        x, y = rotated(u, v)
        return x + dx, y + dy

    snake = _strokes(path, stops, window, selected, radius, o, place)
    snake.icons = [(n, *place(*path.at(stops[n]))) for n in window]
    return snake
