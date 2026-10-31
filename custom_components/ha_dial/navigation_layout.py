"""The navigation designs; renderers receive resolved coordinates only.

Each layout draws its own structure and returns its touch regions and where the settings cog fits.
"""

from .assets import icon_names
from .canvas import Canvas, polar
from .catalogue import CONTROL_TYPES
from .snake_path import arrange


def icon_for(item: dict, options: dict) -> str:
    """An item's icon, preferring the Atlas's fine line look where MDI has an outline."""
    name = (
        item.get("icon")
        or CONTROL_TYPES.get(item.get("entity_id", "").partition(".")[0], (None, None, "mdi:folder"))[2]
    )
    outline = f"{name}-outline"
    return outline if options["icon-style"] == "outline" and outline in icon_names() else name


def chrome(c: Canvas, view: dict, o: dict, y: int) -> list[dict]:
    """Back and home; hiding them leaves the touch regions in place."""
    style, size = o["chrome-style"], o["chrome-size"]
    # Inside a ring of destinations (y 158) the pills must clear the lower items, as in the Atlas.
    breadth = size * (4 if y < 180 else 5)
    y += o["chrome-offset"]
    half = (breadth / 2 if style == "pill" else size) + o["chrome-gap"] / 2
    regions = []
    for name, icon, label, x, present in (
        ("back", "mdi:arrow-left", "BACK", 120 - half, view.get("back")),
        ("home", "mdi:home-outline", "HOME", 120 + half, True),
    ):
        if not present:
            continue
        regions.append({"id": name, "x": round(x), "y": round(y), "r": max(14, size + 4)})
        if style == "hidden":
            continue
        surface, primary = c.theme["surface"], c.theme["primary"]
        if style == "circle":
            c.disc(x, y, size, surface if not c.crisp else c.theme["bg"], c.theme["quiet"])
            c.icon(icon, x, y, round(size * 1.15), primary, surface)
        else:
            c.pill(x, y, breadth, size * 2, surface if not c.crisp else c.theme["bg"], c.theme["quiet"])
            c.icon(icon, x - breadth * 0.3, y, round(size * 1.05), primary, surface)
            c.text(label, x + breadth * 0.14, y, 6, c.theme["text"], surface, tracking=1 if y > 180 else 0, weight=1)
    return regions


def _item(c: Canvas, x, y, item, active, o, under=None) -> dict:
    """The classic ringed destination."""
    theme = c.theme
    radius = o["highlight-radius"] if active else o["icon-size"] // 2 + o["item-padding"]
    fill = c.tint(0.2) if active and not c.crisp else theme["bg"] if c.crisp else theme["surface"]
    c.disc(x, y, radius, fill, theme["primary"] if active else theme["quiet"], o["selected-border"] if active else o["item-border"], under)
    size = o["selected-icon-size"] if active else o["icon-size"]
    c.icon(icon_for(item, o), x, y, size, theme["secondary"] if active else theme["text"], fill)
    return {"id": item["id"], "x": round(x), "y": round(y), "r": max(14, radius)}


def _hub(c: Canvas, o, y=120) -> None:
    if o["hub-visible"]:
        fill = c.theme["bg"] if c.crisp else c.tint(0.08, c.theme["surface"])
        c.disc(120, y, o["hub-radius"], fill, c.theme["grid"], o["hub-border"])


def _hub_under(c: Canvas, o) -> str:
    return c.theme["bg"] if c.crisp or not o["hub-visible"] else c.tint(0.08, c.theme["surface"])


def _title(c: Canvas, label, sub, o, y=104, width=108, under=None) -> None:
    y += o["title-offset"]
    c.text(label.upper(), 120, y, o["font-size"], c.theme["text"], under, tracking=o["tracking"], weight=1, max_width=width)
    c.text(sub, 120, y + o["label-gap"], o["label-size"], c.theme["quiet"] if not c.crisp else c.theme["primary"], under, tracking=1, weight=1, max_width=width)


def _selected_label(items, selected, view):
    if not items:
        return "NO DESTINATIONS"
    return items[selected % len(items)]["label"] if selected < len(items) else "Settings"


def _orbit(c, view, items, selected, o):
    if o["tick-ring"]:
        c.ticks(120, 120, 119 - o["ring-inset"] - o["tick-inset"], o["tick-count"], o["tick-length"], c.theme["quiet"], 5, c.theme["secondary"], o["tick-length"] + 3)
    _hub(c, o)
    regions = []
    for n, item in enumerate(items):
        x, y = polar(120, 120, o["orbit-radius"], n * 360 / max(1, len(items)))
        regions.append(_item(c, x, y, item, n == selected, o))
    under = _hub_under(c, o)
    _title(c, _selected_label(items, selected, view), f"{selected + 1:02}/{len(items):02}" if c.crisp else "TURN TO EXPLORE", o, under=under, width=2 * o["hub-radius"] - 14)
    return regions, 158, 70


def _pointer(c, view, items, selected, o):
    theme = c.theme
    if o["tick-ring"]:
        c.ticks(120, 120, 119 - o["ring-inset"] - o["tick-inset"], o["tick-count"], o["tick-length"], theme["quiet"], 5, theme["secondary"], o["tick-length"] + 3)
    hub = o["hub-radius"]
    if o["hub-visible"]:
        # A dotted inner ring: the pointer rides on it, rather than a solid hub holding the title.
        c.ticks(120, 120, hub, 72, o["hub-border"] + 1, theme["quiet"])
    regions = []
    for n, item in enumerate(items):
        angle = n * 360 / max(1, len(items))
        x, y = polar(120, 120, o["orbit-radius"], angle)
        active = n == selected
        if active:
            regions.append(_item(c, x, y, item, True, o))
            tip = polar(120, 120, hub + o["pointer-size"], angle)
            c.poly([tip, polar(120, 120, hub, angle - 7), polar(120, 120, hub, angle + 7)], theme["primary"])
        else:
            c.icon(icon_for(item, o), x, y, o["icon-size"], theme["quiet"] if not c.crisp else theme["text"])
            regions.append({"id": item["id"], "x": round(x), "y": round(y), "r": 16})
    _title(c, _selected_label(items, selected, view), "SELECTED", o, width=2 * hub - 18)
    return regions, 158, 70


def _rolodex(c, view, items, selected, o):
    theme = c.theme
    count = len(items)
    shown = [(selected + offset) % count for offset in (-1, 0, 1)] if count > 2 else list(range(count))
    height, side = o["row-height"], round(o["row-height"] * 0.65)
    gap = o["row-gap"]
    regions = []
    for slot, n in enumerate(shown):
        active = n == selected
        half = height / 2 if active else side / 2
        if count > 2:
            y = 110 + (slot - 1) * (height / 2 + side / 2 + gap)
        else:
            y = 110 + (slot - (count - 1) / 2) * (height + gap)
        top = o["row-width"] * (1 if active else 0.72 if slot == 0 else 0.8)
        bottom = top - o["row-taper"] if slot < 2 else top - o["row-taper"] * 0.5
        # Perspective: rows lean away from the viewer above and below the selection.
        if slot == 0 and not active:
            top, bottom = bottom, top
        corners = [(120 - top / 2, y - half), (120 + top / 2, y - half), (120 + bottom / 2, y + half), (120 - bottom / 2, y + half)]
        fill = c.tint(0.2) if active else theme["surface"]
        c.surface(corners, fill, theme["primary"] if active else theme["quiet"], hatch=theme["grid"] if active else None)
        for inset in range(1, (o["selected-border"] if active else o["item-border"])):
            inner = [(a + (120 - a) * inset / 60, b + (y - b) * inset / max(1, half)) for a, b in corners]
            c.path([*inner, inner[0]], theme["primary"] if active else theme["quiet"], None if c.crisp else fill)
        under = theme["bg"] if c.crisp else fill
        icon_x = 120 - min(top, bottom) / 2 + (height * 0.75 if active else side * 0.8)
        c.icon(icon_for(items[n], o), icon_x, y, o["selected-icon-size"] if active else o["icon-size"], theme["secondary"] if active else theme["text"], under)
        c.text(items[n]["label"].upper(), 128, y, o["font-size"] if active else max(7, o["font-size"] - 4), theme["text"] if active else theme["secondary"], under, tracking=o["tracking"], weight=1 if active else 0, max_width=min(top, bottom) - (height * 1.3 if active else side * 1.5))
        regions.append({"id": items[n]["id"], "x": 120, "y": round(y), "r": max(10, round(half))})
    right = 120 + o["row-width"] / 2 + 10
    c.path([(right, 100), (right + 8, 110), (right, 120)], theme["primary"])
    return regions, 209, 24


def _petals(c, view, items, selected, o):
    theme = c.theme
    count = max(1, len(items))
    cy = 109
    length, spread = o["petal-length"], min(o["petal-spread"], 170 / count)

    def bezier(end, control):
        return [
            tuple((1 - t) ** 2 * s + 2 * (1 - t) * t * m + t**2 * e for s, m, e in zip((120, cy), control, end))
            for t in (step / 10 for step in range(11))
        ]

    regions = []
    for n, item in enumerate(items):
        angle = n * 360 / count
        active = n == selected
        centre = polar(120, cy, length * 0.72, angle)
        a, b = polar(120, cy, length, angle - spread), polar(120, cy, length, angle + spread)
        outline = bezier(a, centre)
        outline += [polar(120, cy, length, angle - spread + 2 * spread * step / 10) for step in range(1, 10)]
        outline += list(reversed(bezier(b, centre)))
        fill = c.tint(0.22)
        if active:
            c.surface(outline[:-1], fill, theme["primary"], hatch=theme["grid"])
        else:
            c.path(outline, theme["grid"] if not c.crisp else theme["quiet"])
        c.icon(icon_for(item, o), *centre, o["selected-icon-size"] if active else o["icon-size"], theme["secondary"] if active else theme["text"], fill if active and not c.crisp else None)
        regions.append({"id": item["id"], "x": round(centre[0]), "y": round(centre[1]), "r": 18})
    hub = o["hub-radius"] // 2 + 2
    c.disc(120, cy, hub, theme["bg"], theme["quiet"], o["hub-border"])
    c.text(_selected_label(items, selected, view).upper(), 120, cy - 4, min(o["font-size"], 11), theme["text"], tracking=o["tracking"], weight=1, max_width=2 * hub - 10)
    c.text(f"{selected + 1:02} / {len(items):02}", 120, cy + 10, o["label-size"], theme["primary"], tracking=1, weight=1, max_width=2 * hub - 10)
    return regions, 209, 24


def _constellation(c, view, items, selected, o):
    theme = c.theme
    count = max(1, len(items))
    radius = o["orbit-radius"] * 0.72
    # Alternating radii and a rotation give an uneven map, unlike Orbit's even ring.
    nodes = [polar(120, 112, radius + (9 if n % 2 else -5), n * 360 / count + 15) for n in range(count)]
    flat = []
    for n, (x, y) in enumerate(nodes):
        flat.extend((x, y, *nodes[(n + 1) % count]))
    if count > 1:
        c.lines(flat, theme["quiet"])
    regions = []
    for n, item in enumerate(items):
        x, y = nodes[n]
        active = n == selected
        node = o["highlight-radius"] - 4 if active else o["icon-size"] // 2 + o["item-padding"] // 2
        fill = c.tint(0.2) if active and not c.crisp else theme["bg"] if c.crisp else theme["surface"]
        c.disc(x, y, node, fill, theme["primary"] if active else theme["secondary"], o["selected-border"] if active else o["item-border"])
        c.icon(icon_for(item, o), x, y, (o["selected-icon-size"] - 3) if active else o["icon-size"] - 4, theme["text"], fill)
        regions.append({"id": item["id"], "x": round(x), "y": round(y), "r": max(14, node)})
    _title(c, _selected_label(items, selected, view), "CONNECTED PATH", o, y=106, width=round(radius * 1.3))
    return regions, 209, 24


def _compass(c, view, items, selected, o):
    theme = c.theme
    radius = o["orbit-radius"] * 0.62
    c.ring(120, 118, radius + 17, theme["grid"])
    c.lines([120, 118 - radius - 26, 120, 118 + radius + 26, 120 - radius - 26, 118, 120 + radius + 26, 118], theme["grid"])
    page = selected // 4 if selected < len(items) else 0
    regions = []
    for slot, n in enumerate(range(page * 4, min(page * 4 + 4, len(items)))):
        x, y = polar(120, 118, radius, slot * 90)
        regions.append(_item(c, x, y, items[n], n == selected, o))
    hub = o["hub-radius"] // 2 - 3
    fill = theme["bg"] if c.crisp else theme["surface"]
    c.disc(120, 118, hub, fill, theme["quiet"] if c.crisp else theme["surface"], o["hub-border"])
    c.text(_selected_label(items, selected, view).upper(), 120, 118, min(o["font-size"], 13), theme["text"], fill, tracking=o["tracking"], weight=1, max_width=2 * hub + 8)
    return regions, 209, 24


def _ribbon(c, view, items, selected, o):
    theme = c.theme
    count = len(items)
    bend = o["ribbon-bend"]
    start, control, end = (38, 160), (120 - bend, 96 - bend), (202, 60)

    def along(t):
        return tuple((1 - t) ** 2 * s + 2 * (1 - t) * t * m + t**2 * e for s, m, e in zip(start, control, end))

    half = o["ribbon-width"] / 2
    upper, lower, centre = [], [], []
    for step in range(25):
        t = step / 24
        x, y = along(t)
        dx, dy = (along(min(1, t + 0.02))[0] - along(max(0, t - 0.02))[0], along(min(1, t + 0.02))[1] - along(max(0, t - 0.02))[1])
        length = max(0.01, (dx * dx + dy * dy) ** 0.5)
        upper.append((x + dy / length * half, y - dx / length * half))
        lower.append((x - dy / length * half, y + dx / length * half))
        centre.append((x, y))
    band = c.tint(0.2, theme["grid"])
    band_outline = [*upper, *reversed(lower)]
    c.surface(band_outline, band, theme["quiet"], hatch=theme["grid"])
    c.path(centre, theme["primary"], None if c.crisp else band)
    shown = [(selected + offset) % count for offset in range(-2, 3)] if count > 4 else list(range(count))
    regions = []
    for slot, n in enumerate(shown):
        t = (slot + (2.5 - len(shown) / 2)) / 5 + 0.1
        x, y = along(t)
        active = n == selected
        radius = o["highlight-radius"] - 3 if active else o["icon-size"] // 2 + o["item-padding"] // 2
        fill = c.tint(0.25) if active and not c.crisp else theme["bg"] if c.crisp else theme["surface"]
        c.disc(x, y, radius, fill, theme["primary"] if active else theme["quiet"], o["selected-border"] if active else o["item-border"], band)
        c.icon(icon_for(items[n], o), x, y, o["selected-icon-size"] - 4 if active else o["icon-size"] - 4, theme["text"] if active else theme["secondary"], fill)
        regions.append({"id": items[n]["id"], "x": round(x), "y": round(y), "r": max(14, radius)})
    c.text(_selected_label(items, selected, view).upper(), 120, 180, o["font-size"], theme["text"], tracking=o["tracking"], weight=1, max_width=140)
    return regions, 209, 24


def _breadcrumb(c, view, items, selected, o):
    theme = c.theme
    ancestors = view.get("breadcrumbs", [])[-2:]
    layers = [*ancestors, view.get("title", "Home")]
    height, gap = o["layer-height"], o["layer-gap"]
    regions = []
    bottom = 150
    for depth, name in enumerate(reversed(layers)):
        current = depth == 0
        y = bottom - height / 2 - depth * (height + gap)
        width = 120 + depth * 34
        fill = c.tint(0.5, theme["grid"]) if not current else theme["surface"]
        stroke = theme["primary"] if current else theme["quiet"]
        c.pill(120, y, min(190, width), height, None if c.crisp else fill, stroke, o["selected-border"] if current else 1)
        size = max(o["label-size"], o["font-size"] - depth * 3)
        c.text(name.upper(), 120, y, size, theme["text"] if current else theme["quiet"] if depth > 1 else theme["secondary"], None if c.crisp else fill, tracking=o["tracking"], weight=1 if current else 0, max_width=min(190, width) - 22)
    label = _selected_label(items, selected, view).upper()
    c.poly([(120, bottom + 6), (114, bottom + 13), (126, bottom + 13)], theme["primary"])
    c.text(f"{label} {selected + 1}/{len(items)}", 120, bottom + 24, o["label-size"] + 1, theme["primary"], tracking=1, weight=1, max_width=150)
    if items:
        regions.append({"id": items[selected % len(items)]["id"], "x": 120, "y": bottom - height // 2, "r": max(14, height // 2)})
    return regions, 209, 24


def _list(c, view, items, selected, o):
    """A plain list: the only design that reads long labels comfortably."""
    theme = c.theme
    count = len(items)
    pitch = o["row-height"] // 2 + o["row-gap"] + 6
    window = 5
    first = max(0, min(selected - window // 2, count - window)) if count > window else 0
    middle = 104
    regions = []
    for slot, n in enumerate(range(first, min(first + window, count))):
        y = middle + (slot - (min(window, count) - 1) / 2) * pitch
        active = n == selected
        half = max(40, 84**2 - (y - 120) ** 2) ** 0.5  # Keep each row inside the round display.
        left = 120 - half + 8
        if active:
            fill = c.tint(0.2)
            c.pill(120, y, half * 2 - 8, pitch - 3, None if c.crisp else fill, theme["primary"], o["selected-border"], radius=4)
        under = None if c.crisp or not active else c.tint(0.2)
        c.icon(icon_for(items[n], o), left + 10, y, o["selected-icon-size"] - 5 if active else o["icon-size"] - 3, theme["secondary"] if active else theme["quiet"], under)
        c.text(items[n]["label"], left + 25, y, o["font-size"] if active else max(7, o["font-size"] - 3), theme["text"] if active else theme["secondary"], under, align="start", tracking=o["tracking"], weight=1 if active else 0, max_width=half * 2 - 44)
        regions.append({"id": items[n]["id"], "x": 120, "y": round(y), "r": max(10, pitch // 2)})
    if count > window:
        c.arc(120, 120, 96, 60, 120, theme["grid"], 2)
        c.arc(120, 120, 96, 60 + 60 * first / count, 60 + 60 * (first + window) / count, theme["primary"], 2, under=theme["grid"])
    return regions, 209, 24


def _grid(c, view, items, selected, o):
    """Tiles, paged nine at a time: many destinations visible at once."""
    theme = c.theme
    page = selected // 9 if selected < len(items) else 0
    shown = items[page * 9 : page * 9 + 9]
    size = o["icon-size"] + 2 * o["item-padding"] + 8
    pitch = size + o["row-gap"]
    regions = []
    rows = (len(shown) + 2) // 3
    for slot, item in enumerate(shown):
        column, row = slot % 3, slot // 3
        x, y = 120 + (column - 1) * pitch, 100 + (row - (rows - 1) / 2) * pitch
        active = page * 9 + slot == selected
        fill = c.tint(0.2) if active else theme["surface"]
        border = o["selected-border"] if active else o["item-border"]
        c.pill(x, y, size, size, None if c.crisp else fill, theme["primary"] if active else theme["quiet"], border, radius=8)
        c.icon(icon_for(item, o), x, y, o["selected-icon-size"] if active else o["icon-size"], theme["secondary"] if active else theme["text"], None if c.crisp else fill)
        regions.append({"id": item["id"], "x": round(x), "y": round(y), "r": max(12, size // 2)})
    c.text(_selected_label(items, selected, view).upper(), 120, 186, o["font-size"] - 2, theme["text"], tracking=o["tracking"], weight=1, max_width=130)
    return regions, 209, 24


def _pager(c, view, items, selected, o):
    """One destination at a time, huge, with its neighbours only hinted at."""
    theme = c.theme
    count = max(1, len(items))
    glow = c.tint(0.1)
    if selected < len(items):
        radius = o["highlight-radius"] + 26
        c.disc(120, 88, radius, theme["bg"] if c.crisp else glow, theme["primary"], o["selected-border"])
        c.icon(icon_for(items[selected], o), 120, 88, o["selected-icon-size"] + 26, theme["secondary"], None if c.crisp else glow)
    c.text(_selected_label(items, selected, view).upper(), 120, 152 + o["title-offset"], o["font-size"] + 4, theme["text"], tracking=o["tracking"], weight=1, max_width=170)
    # A window of dots: an Explorer's page can be long, and each dot is a scene element.
    dots = min(count, 15)
    first = max(0, min(selected - dots // 2, count - dots))
    spacing = min(10, 150 // dots)
    for index in range(first, first + dots):
        x = 120 + (index - first - (dots - 1) / 2) * spacing
        if index == selected:
            c.disc(x, 176, 3, theme["primary"], None)
        else:
            c.disc(x, 176, 1, theme["quiet"], None)
    regions = [{"id": items[selected]["id"], "x": 120, "y": 88, "r": 40}] if selected < len(items) else []
    return regions, 209, 24


def _needle(c, view, items, selected, o):
    """An instrument: the selection is a needle swinging across a scale of destinations."""
    theme = c.theme
    count = max(1, len(items))
    cy = 138
    radius = o["orbit-radius"] - 6
    sweep = 200
    angle_of = lambda n: -sweep / 2 + (sweep * n / (count - 1) if count > 1 else sweep / 2)
    c.arc(120, cy, radius - 18, -sweep / 2 - 6, sweep / 2 + 6, theme["grid"])
    c.ticks(120, cy, radius - 18, count * 4 - 3 if count > 1 else 1, 3, theme["quiet"], 4, theme["secondary"], 7, start=-sweep / 2, sweep=sweep)
    regions = []
    for n, item in enumerate(items):
        x, y = polar(120, cy, radius, angle_of(n))
        active = n == selected
        c.icon(icon_for(item, o), x, y, o["selected-icon-size"] if active else o["icon-size"], theme["secondary"] if active else theme["quiet"])
        regions.append({"id": item["id"], "x": round(x), "y": round(y), "r": 15})
    if selected < len(items):
        tip = polar(120, cy, radius - 24, angle_of(selected))
        c.line(120, cy, *tip, theme["primary"], o["selected-border"] + 1)
    c.disc(120, cy, 7, theme["primary"], None)
    c.text(_selected_label(items, selected, view).upper(), 120, cy + 26, o["font-size"], theme["text"], tracking=o["tracking"], weight=1, max_width=150)
    return regions, 209, 24


def _snake(c, view, items, selected, o):
    """Rows joined by U-turns, so turning the dial follows one unbroken line."""
    theme = c.theme
    snake = arrange(len(items), selected, o, o["icon-size"] // 2 + o["item-padding"])
    line = o.get("snake-line", theme["quiet"])
    inks = {False: line, True: o.get("snake-travelled", theme["primary"]) if o["snake-lit"] else line}
    width = o["snake-width"]
    for travelled, ink in inks.items():
        strokes = [stroke[:4] for stroke in snake.lines if stroke[4] is travelled]
        if width == 1 and strokes:
            c.lines([value for stroke in strokes for value in stroke], ink)
        elif width > 1:
            for stroke in strokes:
                c.line(*stroke, ink, width)
    for x, y, r, start, end, travelled in snake.arcs:
        c.arc(x, y, r, start, end, inks[travelled], width)
    regions = [_item(c, x, y, items[n], n == selected, o) for n, x, y in snake.icons]
    c.text(_selected_label(items, selected, view).upper(), 120, 182 + o["title-offset"], o["font-size"], theme["text"], tracking=o["tracking"], weight=1, max_width=140)
    return regions, 209, 24


LAYOUTS = {
    "NAV-SNAKE": _snake,
    "NAV-LIST": _list,
    "NAV-GRID": _grid,
    "NAV-PAGER": _pager,
    "NAV-NEEDLE": _needle,
    "NAV-ORBIT": _orbit,
    "NAV-POINTER": _pointer,
    "NAV-ROLODEX": _rolodex,
    "NAV-PETALS": _petals,
    "NAV-CONSTELLATION": _constellation,
    "NAV-COMPASS": _compass,
    "NAV-RIBBON": _ribbon,
    "NAV-BREADCRUMB": _breadcrumb,
}


def navigation_layout(c: Canvas, view: dict, o: dict):
    """Draw a menu; returns regions and the settings cog's position."""
    items = [item for item in view.get("items", []) if not item.get("settings")]
    selected = view.get("selected", 0)
    regions, footer, cog = LAYOUTS.get(view.get("style", ""), _orbit)(c, view, items, selected, o)
    return regions + chrome(c, view, o, footer), cog
