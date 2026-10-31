"""The Atlas's domain graphics, drawing only what HA actually reports.

Where the prototype showed sample data HA doesn't supply (a floor map, a history trace), the graphic
draws from real attributes instead. Nothing here invents a reading.
"""

from math import cos, pi, sin

from .assets import icon_names
from .canvas import Canvas, polar

WEATHER_ICONS = {
    "clear-night": "mdi:weather-night", "cloudy": "mdi:weather-cloudy", "fog": "mdi:weather-fog", "hail": "mdi:weather-hail",
    "lightning": "mdi:weather-lightning", "lightning-rainy": "mdi:weather-lightning-rainy", "partlycloudy": "mdi:weather-partly-cloudy",
    "pouring": "mdi:weather-pouring", "rainy": "mdi:weather-rainy", "snowy": "mdi:weather-snowy", "snowy-rainy": "mdi:weather-snowy-rainy",
    "sunny": "mdi:weather-sunny", "windy": "mdi:weather-windy", "windy-variant": "mdi:weather-windy-variant",
}


def icon_name(view: dict, o: dict) -> str:
    name = view.get("icon") or "mdi:information-outline"
    outline = f"{name}-outline"
    return outline if o["icon-style"] == "outline" and outline in icon_names() else name


def _value(c, view, o, y: float = 116, size=None, under=None):
    from .control_layout import value_element

    value_element(c, view, o, 120, y + o["value-offset"], size or o["value-size"], under)


def _detail(c, view, o, y=170, width=130, under=None):
    from .control_layout import detail_text

    if view.get("actions") or view.get("confirmation"):
        y = min(y, 155)
    c.text(detail_text(view), 120, y + o["detail-offset"], o["detail-size"], c.theme["quiet"], under, tracking=o["tracking"], weight=1, max_width=width)


def _percent(view):
    from .control_layout import percent_of

    return percent_of(view)


def gauge_ring(c: Canvas, view: dict, o: dict, icon=True, continuous=None) -> None:
    """Track, value and scale: the Atlas's lighting instrument, and the default for any level."""
    theme = c.theme
    radius, half = o["gauge-radius"], o["gauge-sweep"] / 2
    track = o["track-width"]
    centre = 118
    c.arc(120, centre, radius, -half, half, theme["grid"], track, o["gauge-caps"])
    live = view.get("continuous") or view.get("domain") in {"light", "cover"}
    active = view.get("domain") != "light" or view.get("active", True)
    if live:
        accent = theme["primary"] if active or view.get("pending") else theme["quiet"]
        c.gauge(
            120, centre, radius, -half, half, _percent(view), accent, o["gauge-width"], fill=theme["primary"],
            minimum=view.get("minimum", 0), maximum=view.get("maximum", 100), cap=o["gauge-caps"], under=theme["grid"],
        )
    count, length = o["gauge-tick-count"], o["gauge-tick-length"]
    outer = radius - track / 2 - o["gauge-tick-gap"]
    lit = round(_percent(view) * (count - 1) / 100) if live else -1
    bright, dim = [], []
    for index in range(count):
        angle = -half + index * 2 * half / (count - 1)
        (bright if index <= lit else dim).extend((*polar(120, centre, outer - length, angle), *polar(120, centre, outer, angle)))
    if bright:
        c.lines(bright, theme["secondary"])
    if dim:
        c.lines(dim, theme["grid"])
    if icon:
        c.icon(icon_name(view, o), 120, 74, o["selected-icon-size"], theme["secondary"])
    _value(c, view, o)
    _detail(c, view, o)


def _thermostat(c, view, o):
    """The ring plus a mode pill: target and mode are what matter on a thermostat."""
    gauge_ring(c, view, o, icon=False)
    mode = str(view.get("state", "")).replace("_", " ").upper()
    if mode:
        c.text(mode, 120, 78, 8, c.theme["primary"], tracking=2, weight=1, max_width=80)


def _volume(c, view, o):
    """Radial bars grow with the level, a little like a waveform."""
    theme = c.theme
    radius = o["gauge-radius"]
    half = o["gauge-sweep"] / 2
    count = max(9, o["gauge-tick-count"])
    lit = round(_percent(view) * (count - 1) / 100)
    bright, dim = [], []
    for index in range(count):
        angle = -half + index * 2 * half / (count - 1)
        reach = 6 + (index % 3) * 3
        target = bright if index <= lit else dim
        target.extend((*polar(120, 118, radius - reach, angle), *polar(120, 118, radius + reach, angle)))
    if dim:
        c.lines(dim, theme["grid"])
    if bright:
        c.lines(bright, theme["primary"])
    c.gauge(120, 118, radius - 16, -half, half, _percent(view), theme["secondary"], max(1, o["gauge-width"] // 3), minimum=view.get("minimum", 0), maximum=view.get("maximum", 100))
    _value(c, view, o)
    _detail(c, view, o)


def _media(c, view, o):
    """A record in a sleeve, with the title beside it and volume around the record."""
    theme = c.theme
    fill = c.tint(0.14, theme["surface"])
    c.pill(120, 92, 138, 86, None if c.crisp else fill, theme["quiet"], 1, radius=13)
    under = None if c.crisp else fill
    c.disc(84, 92, 30, c.tint(0.2) if not c.crisp else theme["bg"], theme["primary"], 1, fill)
    c.disc(84, 92, 9, theme["bg"], theme["primary"] if c.crisp else None, 1, c.tint(0.2))
    c.gauge(84, 92, 36, -180, 180, _percent(view), theme["secondary"], 2, minimum=view.get("minimum", 0), maximum=view.get("maximum", 100), under=fill)
    title = str(view.get("detail", view.get("state", ""))).upper().split()
    middle = (len(title) + 1) // 2
    c.text(" ".join(title[:middle]), 123, 82, 10, theme["text"], under, align="start", tracking=1, weight=1, max_width=62)
    c.text(" ".join(title[middle:]), 123, 96, 10, theme["text"], under, align="start", tracking=1, weight=1, max_width=62)
    c.text(str(view.get("state", "")).upper(), 123, 112, 6, theme["quiet"], under, align="start", tracking=1, weight=1, max_width=62)
    _detail(c, {**view, "detail": f"VOLUME {round(view.get('value', 0))}%"}, o, y=151)


def _cover(c, view, o):
    """Slats drop with the position; 100 is open, so the lit slats are the covered part."""
    theme = c.theme
    left, top, width, height = 68, 49, 104, 112
    c.pill(120, top + height / 2, width, height, None if c.crisp else theme["surface"], theme["quiet"], 1, radius=7)
    under = None if c.crisp else theme["surface"]
    count = 7
    closed = round((100 - _percent(view)) * count / 100)
    flat_on, flat_off = [], []
    for index in range(count):
        y = top + 10 + index * (height - 20) / (count - 1)
        target = flat_on if index < closed else flat_off
        for row in range(3 if not c.crisp else 2):
            target.extend((left + 6, y + row, left + width - 6, y + row))
    if flat_off:
        c.lines(flat_off, theme["grid"], under)
    if flat_on:
        c.lines(flat_on, theme["primary"], under)
    c.gauge(120, top + height / 2, 68, 62, 118, _percent(view), theme["secondary"], 2, minimum=view.get("minimum", 0), maximum=view.get("maximum", 100))
    _value(c, view, o, y=top + height / 2, under=under)
    _detail(c, view, o)


def _fan(c, view, o):
    """Five turbine blades around the speed."""
    theme = c.theme
    cy = 104
    c.disc(120, cy, 60, theme["bg"] if c.crisp else theme["surface"], theme["quiet"], 1)
    under = None if c.crisp else theme["surface"]
    blade = c.tint(0.45 if view.get("active", True) else 0.14)
    for index in range(5):
        base = index * 72
        points = []
        for step in range(13):
            t = step / 12 * 2 * pi
            along, across = 34 + 21 * cos(t), 12 * sin(t)
            angle = (base - 90) * pi / 180
            points.append((120 + along * cos(angle) - across * sin(angle), cy + along * sin(angle) + across * cos(angle)))
        if c.crisp:
            c.path([*points, points[0]], theme["primary"])
        else:
            c.poly(points, blade, theme["surface"])
    c.disc(120, cy, 18, theme["bg"], theme["secondary"], 1, under)
    _value(c, view, o, y=cy, size=min(o["value-size"], 20))
    c.gauge(120, cy, 68, -132, 132, _percent(view), theme["primary"], 2, minimum=view.get("minimum", 0), maximum=view.get("maximum", 100))
    _detail(c, view, o, y=172)


def _sentinel(c, view, o):
    """Security and access: a tick ring around a large symbol, with a sober state beneath."""
    theme = c.theme
    cy = 92
    c.disc(120, cy, 54, theme["bg"] if c.crisp else c.tint(0.05), theme["grid"], 1)
    c.ticks(120, cy, 50, 24, 3, theme["quiet"], 3, theme["secondary"], 6)
    c.icon(icon_name(view, o), 120, cy, 44, theme["primary"], None if c.crisp else c.tint(0.05))
    state = str(view.get("state", "--")).replace("_", " ").upper()
    if not view.get("available", True):
        state = "--"
    c.text(state, 120, 156, 15, theme["text"], tracking=1, weight=1, max_width=150)
    from .control_layout import detail_text

    pending = detail_text(view)
    if pending in {"PENDING", "UNAVAILABLE"}:
        c.text(pending, 120, 170, o["detail-size"], theme["quiet"], tracking=1, weight=1)


def _vacuum(c, view, o):
    """Battery around the robot: HA reports charge and state, and no floor map."""
    theme = c.theme
    cy = 90
    battery = view.get("battery")
    c.arc(120, cy, 56, -180, 180, theme["grid"], 3)
    if battery is not None:
        c.arc(120, cy, 56, -180, -180 + 360 * battery / 100, theme["primary"], 3)
    c.icon(icon_name(view, o), 120, cy - 8, 36, theme["secondary"])
    c.text(f"{round(battery)}%" if battery is not None else "--", 120, cy + 24, 14, theme["text"], tracking=0, weight=1)
    c.text(str(view.get("state", "--")).replace("_", " ").upper(), 120, 158 if view.get("actions") else 168, 8, theme["primary"], tracking=2, weight=1, max_width=130)


def _measure(icon_size=30, lines=5):
    """A sensor reading over a ruled field: the plot itself belongs to the Data faces, with history."""

    def draw(c, view, o):
        theme = c.theme
        flat = []
        for index in range(lines):
            y = 62 + index * 22
            half = (82 ** 2 - (y - 118) ** 2) ** 0.5 if abs(y - 118) < 82 else 0
            flat.extend((120 - half, y, 120 + half, y))
        c.lines(flat, theme["grid"])
        c.icon(icon_name(view, o), 120, 72, icon_size, theme["primary"])
        _value(c, view, o, y=116, size=o["value-size"])
        _detail(c, view, o)

    return draw


def _air(c, view, o):
    """Calm concentric rings around the reading."""
    theme = c.theme
    for radius, colour in ((74, theme["grid"]), (64, theme["grid"]), (54, theme["quiet"])):
        c.ring(120, 112, radius, colour)
    c.icon(icon_name(view, o), 120, 80, 18, theme["primary"])
    _value(c, view, o, y=114, size=o["value-size"])
    _detail(c, view, o, y=176)


def _weather(c, view, o):
    """A large condition symbol, with temperature set against it."""
    theme = c.theme
    icon = WEATHER_ICONS.get(view.get("state"), "mdi:weather-partly-cloudy")
    c.icon(icon, 90, 90, 64, theme["primary"])
    temperature = str(view.get("detail", "--")).split(" / ")[0]
    c.text(temperature, 168, 102, 18, theme["text"], tracking=0, weight=1, max_width=64)
    c.text(str(view.get("state", "--")).replace("-", " ").upper(), 120, 152, 8, theme["secondary"], tracking=2, weight=1, max_width=150)


def _timer(c, view, o):
    """A full dominant ring around the time remaining."""
    theme = c.theme
    active = view.get("state") == "active"
    buttons = bool(view.get("actions"))
    cy, radius = (98, o["gauge-radius"] - 12) if buttons else (112, o["gauge-radius"])
    c.arc(120, cy, radius, -180, 180, theme["primary"] if active else theme["grid"], o["gauge-width"])
    c.ticks(120, cy, radius - o["gauge-width"] - 3, 60, 2, theme["quiet"], 5, theme["secondary"], 6)
    c.text(str(view.get("detail", "--")), 120, cy - 4, min(o["value-size"], 26), theme["text"], tracking=0, weight=1, max_width=radius * 2 - 24)
    c.text(str(view.get("state", "--")).upper(), 120, cy + 20, 7, theme["primary"], tracking=2, weight=1)


def _calendar(c, view, o):
    """The next event, wrapped into the centre of a day ring."""
    theme = c.theme
    c.disc(120, 104, 62, theme["bg"] if c.crisp else theme["surface"], theme["quiet"], 1)
    under = None if c.crisp else theme["surface"]
    busy = view.get("state") == "on"
    for index in range(12):
        x, y = polar(120, 104, 52, index * 30)
        c.disc(x, y, 5 if busy and index == 0 else 2, theme["primary"] if index == 0 else theme["quiet"], None, 1, under)
    words = str(view.get("detail", "No event")).upper().split()
    middle = (len(words) + 1) // 2
    c.text(" ".join(words[:middle]), 120, 96, 11, theme["text"], under, tracking=1, weight=1, max_width=84)
    c.text(" ".join(words[middle:]), 120, 112, 11, theme["text"], under, tracking=1, weight=1, max_width=84)
    c.text("NOW" if busy else "NEXT", 120, 174, 7, theme["primary"], tracking=2, weight=1)


def _scene(c, view, o):
    """A small composed landscape: a scene is a mood, so this one is allowed to be decorative."""
    theme = c.theme
    cy = 92
    c.disc(120, cy, 52, theme["bg"] if c.crisp else theme["surface"], theme["quiet"], 1)
    under = None if c.crisp else theme["surface"]
    c.disc(98, cy - 18, 11, c.tint(0.5, theme["secondary"]), None, 1, under)
    hills = [(78, cy + 20), (98, cy + 2), (120, cy + 16), (142, cy - 6), (162, cy + 20), (146, cy + 36), (94, cy + 36)]
    if c.crisp:
        c.path([*hills, hills[0]], theme["primary"])
    else:
        c.poly(hills, c.tint(0.3), theme["surface"])
    flat = []
    for index in range(9):
        x, y = 90 + (index * 29) % 64, cy - 36 + (index * 17) % 28
        flat.extend((x, y, x, y))
    c.lines(flat, theme["secondary"], under)
    c.text("ACTIVATE", 120, 155 if view.get("actions") else 168, 10, theme["text"], tracking=2, weight=1)


def _selector(c, view, o):
    """An option wheel: real options around the ring, the current one in the middle."""
    theme = c.theme
    options = view.get("options") or []
    cy = 104
    c.disc(120, cy, 64, theme["bg"] if c.crisp else theme["surface"], theme["quiet"], 1)
    under = None if c.crisp else theme["surface"]
    current = max(0, min(len(options) - 1, round(view.get("value", 0)))) if options else 0
    shown = options[:8]
    for index, option in enumerate(shown):
        x, y = polar(120, cy, 48, index * 360 / max(1, len(shown)))
        c.text(str(option).upper(), x, y, 6, theme["secondary"] if index == current else theme["quiet"], under, tracking=0, weight=1, max_width=36)
    fill = c.tint(0.2)
    c.disc(120, cy, 25, fill if not c.crisp else theme["bg"], theme["primary"], 1, under)
    label = str(options[current]).upper() if options else str(view.get("state", "--")).upper()
    c.text(label, 120, cy, 10, theme["text"], None if c.crisp else fill, tracking=0, weight=1, max_width=46)
    _detail(c, {**view, "detail": f"{current + 1} OF {len(options)}"} if options else view, o, y=178)


def _switch(c, view, o):
    """A large physical toggle."""
    theme = c.theme
    on = view.get("active", False)
    width, height = 110, 54
    fill = c.tint(0.3) if on else theme["surface"]
    c.pill(120, 104, width, height, None if c.crisp else fill, theme["primary"] if on else theme["quiet"], 2)
    x = 120 + (width / 2 - height / 2) * (1 if on else -1)
    c.disc(x, 104, height / 2 - 6, theme["primary"] if on else theme["quiet"], None, 1, None if c.crisp else fill)
    c.icon(icon_name(view, o), 120 + (-30 if on else 30), 104, 22, theme["text"] if on else theme["quiet"], None if c.crisp else fill)
    c.text("ON" if on else "OFF", 120, 148, 18, theme["text"], tracking=2, weight=1)


GRAPHICS = {
    "LIGHT": gauge_ring,
    "THERMOSTAT": _thermostat,
    "VOLUME": _volume,
    "MEDIA": _media,
    "COVER": _cover,
    "FAN": _fan,
    "SECURITY": _sentinel,
    "LOCK": _sentinel,
    "VACUUM": _vacuum,
    "ENERGY": _measure(),
    "WATER": _measure(icon_size=24, lines=3),
    "VEHICLE": _measure(icon_size=40, lines=2),
    "DATA": _measure(icon_size=18, lines=4),
    "AIR": _air,
    "WEATHER": _weather,
    "TIMER": _timer,
    "CALENDAR": _calendar,
    "SCENE": _scene,
    "SELECTOR": _selector,
    "SWITCH": _switch,
}

# These draw their own reading, so the generic unit below the value would be stray.
NO_UNIT = {"MEDIA", "WEATHER", "SWITCH", "VACUUM", "TIMER", "CALENDAR", "SCENE", "SECURITY", "LOCK", "SELECTOR"}
