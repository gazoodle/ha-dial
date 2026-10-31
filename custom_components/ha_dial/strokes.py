"""Crisp's type and icons as plain strokes; the renderers step them with Bresenham.

Crisp never thresholds vector glyphs: the owner ruled that out on 2026-10-30 because it leaves
pseudo-random pixels. Everything here reduces to line segments in display pixels.
"""

import json
import unicodedata
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

RESOURCES = Path(__file__).with_name("resources")

# Single-stroke capitals on a grid 4 wide and 6 tall.
GLYPHS = {
    "A": [[(0, 6), (0, 2), (2, 0), (4, 2), (4, 6)], [(0, 4), (4, 4)]],
    "B": [[(0, 3), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3)]],
    "C": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    "D": [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 1), (3, 0), (0, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "F": [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]],
    "G": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3), (2, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(1, 0), (3, 0)], [(2, 0), (2, 6)], [(1, 6), (3, 6)]],
    "J": [[(4, 0), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "K": [[(0, 0), (0, 6)], [(4, 0), (0, 3), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]],
    "P": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]],
    "Q": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)], [(2, 4), (4, 6)]],
    "R": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)], [(2, 3), (4, 6)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1, 6), (2, 3), (3, 6), (4, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    "0": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)], [(0, 5), (4, 1)]],
    "1": [[(1, 1), (2, 0), (2, 6)], [(1, 6), (3, 6)]],
    "2": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (0, 6), (4, 6)]],
    "3": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)], [(1, 3), (3, 3)]],
    "4": [[(3, 6), (3, 0), (0, 4), (4, 4)]],
    "5": [[(4, 0), (0, 0), (0, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6)]],
    "6": [[(3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]],
    "7": [[(0, 0), (4, 0), (2, 6)]],
    "8": [[(1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3)]],
    "9": [[(1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (4, 3)]],
    ".": [[(2, 5), (2, 6)]],
    ",": [[(2, 5), (1, 7)]],
    ":": [[(2, 1), (2, 2)], [(2, 4), (2, 5)]],
    ";": [[(2, 1), (2, 2)], [(2, 4), (1, 6)]],
    "-": [[(1, 3), (3, 3)]],
    "–": [[(0, 3), (4, 3)]],
    "+": [[(2, 1), (2, 5)], [(0, 3), (4, 3)]],
    "=": [[(0, 2), (4, 2)], [(0, 4), (4, 4)]],
    "/": [[(0, 6), (4, 0)]],
    "\\": [[(0, 0), (4, 6)]],
    "%": [[(0, 6), (4, 0)], [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], [(3, 5), (4, 5), (4, 6), (3, 6), (3, 5)]],
    "°": [[(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]],
    "'": [[(2, 0), (2, 1)]],
    '"': [[(1, 0), (1, 1)], [(3, 0), (3, 1)]],
    "(": [[(3, 0), (2, 1), (2, 5), (3, 6)]],
    ")": [[(1, 0), (2, 1), (2, 5), (1, 6)]],
    "[": [[(3, 0), (2, 0), (2, 6), (3, 6)]],
    "]": [[(1, 0), (2, 0), (2, 6), (1, 6)]],
    "!": [[(2, 0), (2, 4)], [(2, 5), (2, 6)]],
    "?": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (2, 3), (2, 4)], [(2, 5), (2, 6)]],
    "#": [[(1, 1), (1, 5)], [(3, 1), (3, 5)], [(0, 2), (4, 2)], [(0, 4), (4, 4)]],
    "&": [[(4, 6), (1, 2), (1, 1), (2, 0), (3, 1), (3, 2), (0, 4), (0, 5), (1, 6), (2, 6), (4, 4)]],
    "_": [[(0, 6), (4, 6)]],
    "·": [[(2, 3), (2, 3)]],
    "²": [[(1, 0), (3, 0), (3, 1), (1, 2), (3, 2)]],
    "³": [[(1, 0), (3, 0), (2, 1), (3, 2), (1, 2)]],
    "µ": [[(0, 7), (0, 2)], [(0, 5), (1, 6), (3, 6), (4, 5), (4, 2)]],
}
# Anything outside the set is shown as an honest box, never dropped.
MISSING = [[(0, 0), (4, 0), (4, 6), (0, 6), (0, 0)]]


def text_metrics(height: int) -> tuple[float, float]:
    """Grid scale for a cap height; thin, slightly narrow letters keep the line-step visible."""
    return height * 0.75 / 6, height / 6


def _folded(text: str) -> str:
    """Upper-case and strip accents: the stroke set is deliberately small."""
    decomposed = unicodedata.normalize("NFKD", str(text).upper())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def text_width(text: str, height: int, tracking: int) -> int:
    sx, _ = text_metrics(height)
    text = _folded(text)
    if not text:
        return 0
    return len(text) * (round(4 * sx) + 1 + tracking) - tracking - 1


@lru_cache(maxsize=256)
def text_segments(text: str, height: int, tracking: int) -> tuple:
    """Segments relative to the text's top-left. A glyph lands on the same pixels every time."""
    sx, sy = text_metrics(height)
    advance = round(4 * sx) + 1 + tracking
    segments = []
    for position, character in enumerate(_folded(text)):
        if character == " ":
            continue
        origin = position * advance
        for path in GLYPHS.get(character, MISSING):
            points = [(origin + round(x * sx), round(y * sy)) for x, y in path]
            if len(points) == 2 and points[0] == points[1]:
                segments.append((*points[0], *points[1]))
            for a, b in pairwise(points):
                if a != b:
                    segments.append((*a, *b))
    return tuple(segments)


@lru_cache(maxsize=1)
def _stroke_icons() -> dict:
    return json.loads((RESOURCES / "stroke_icons.json").read_text())


# MDI names with a hand-drawn Atlas stroke equivalent; everything else is traced from MDI.
ATLAS_ICONS = {
    "arrow-left": "back", "home": "home", "office-building": "building", "layers": "floor",
    "floor-plan": "room", "lightbulb": "light", "thermometer": "climate", "play-circle": "media",
    "speaker": "speaker", "blinds": "cover", "fan": "fan", "lock": "lock", "shield-home": "shield",
    "robot-vacuum": "vacuum", "lightning-bolt": "energy", "chart-line": "graph",
    "weather-partly-cloudy": "weather", "air-filter": "air", "timer": "timer", "calendar": "calendar",
    "car": "car", "water": "water", "palette": "scene", "camera": "camera", "play": "play",
    "pause": "pause", "plus": "plus", "minus": "minus", "weather-night": "moon",
    "weather-sunny": "sun", "dots-horizontal": "more",
}


def _trace(grid: list[list[bool]]) -> list[list[tuple[int, int]]]:
    """Closed boundary loops of a boolean grid, as a chain of unit edges."""
    edges: dict[tuple[int, int], list[tuple[int, int]]] = {}
    height, width = len(grid), len(grid[0])
    on = lambda x, y: 0 <= x < width and 0 <= y < height and grid[y][x]
    for y in range(height):
        for x in range(width):
            if not grid[y][x]:
                continue
            if not on(x, y - 1):
                edges.setdefault((x, y), []).append((x + 1, y))
            if not on(x + 1, y):
                edges.setdefault((x + 1, y), []).append((x + 1, y + 1))
            if not on(x, y + 1):
                edges.setdefault((x + 1, y + 1), []).append((x, y + 1))
            if not on(x - 1, y):
                edges.setdefault((x, y + 1), []).append((x, y))
    loops = []
    while edges:
        start = next(iter(edges))
        point, loop = start, [start]
        while True:
            targets = edges[point]
            target = targets.pop()
            if not targets:
                del edges[point]
            loop.append(target)
            point = target
            if point == start:
                break
        loops.append(loop)
    return loops


def _simplify(points: list, tolerance: float) -> list:
    """Ramer-Douglas-Peucker: a contour of unit edges becomes a few honest straight strokes."""
    if len(points) < 3:
        return points
    (ax, ay), (bx, by) = points[0], points[-1]
    dx, dy = bx - ax, by - ay
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0:
        distances = [((x - ax) ** 2 + (y - ay) ** 2) ** 0.5 for x, y in points]
    else:
        distances = [abs(dy * (x - ax) - dx * (y - ay)) / length for x, y in points]
    furthest = max(range(len(points)), key=distances.__getitem__)
    if distances[furthest] <= tolerance:
        return [points[0], points[-1]]
    return _simplify(points[: furthest + 1], tolerance)[:-1] + _simplify(points[furthest:], tolerance)


@lru_cache(maxsize=64)
def _traced(name: str) -> tuple:
    """Outline an MDI glyph at high resolution, in the 24-unit icon grid."""
    from PIL import Image, ImageDraw, ImageFont

    from .assets import icon_names

    size = 96
    font = ImageFont.truetype(str(RESOURCES / "mdi.ttf"), size)
    image = Image.new("L", (size, size))
    glyph = chr(icon_names()[name])
    box = font.getbbox(glyph)
    ImageDraw.Draw(image).text(((size - box[2] + box[0]) / 2 - box[0], (size - box[3] + box[1]) / 2 - box[1]), glyph, font=font, fill=255)
    data = image.tobytes()
    grid = [[data[y * size + x] > 127 for x in range(size)] for y in range(size)]
    paths = []
    for loop in _trace(grid):
        if len(loop) < 24:  # Specks disappear at any display size.
            continue
        # A closed loop is simplified as two halves, so its ends stay anchored.
        middle = len(loop) // 2
        points = _simplify(loop[: middle + 1], 2.0)[:-1] + _simplify(loop[middle:], 2.0)
        paths.append([(x / 4, y / 4) for x, y in points])
    return tuple(tuple(path) for path in paths)


def icon_paths(name: str) -> tuple:
    """Polylines for an icon in a 24-unit grid, whichever source supplies them."""
    bare = name.removeprefix("mdi:").removesuffix("-outline")
    atlas = ATLAS_ICONS.get(bare)
    if atlas in _stroke_icons():
        return tuple(tuple((x, y) for x, y in path) for path in _stroke_icons()[atlas])
    return _traced(name)


@lru_cache(maxsize=256)
def icon_segments(name: str, size: int) -> tuple:
    """Segments relative to the icon's top-left, scaled to its display size."""
    scale = size / 24
    segments = []
    for path in icon_paths(name):
        points = [(round(x * scale), round(y * scale)) for x, y in path]
        for a, b in pairwise(points):
            if a != b:
                segments.append((*a, *b))
    return tuple(segments)
