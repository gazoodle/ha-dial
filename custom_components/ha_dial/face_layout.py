"""Ambient, smartwatch and data faces, drawn only from HA's real sources.

A source that isn't configured or available reads as "--": the prototype's sample figures have no
place on a device people believe. Crisp treats fills as line work, which is where its moiré lives.
"""

from .canvas import Canvas, polar
from .control_graphics import WEATHER_ICONS


def _time(clock):
    return f"{clock['hour']:02}:{clock['minute']:02}"


def _ticks(c, o, r=None):
    if o["tick-ring"]:
        c.ticks(120, 120, r or 119 - o["ring-inset"] - o["tick-inset"], o["tick-count"], o["tick-length"], c.theme["quiet"], 5, c.theme["secondary"], o["tick-length"] + 3)


def _big_time(c, clock, o, y=118, size=None):
    c.text(_time(clock), 120, y + o["title-offset"], size or o["value-size"], c.theme["text"], tracking=0, weight=0 if c.crisp else 1)


def _metrics(clock, count):
    metrics = list(clock.get("metrics", []))[:count]
    blank = {"label": "NOT SET", "value": None, "text": "--", "unit": "", "percent": None, "series": []}
    return metrics + [blank] * (count - len(metrics))


def _reading(metric):
    return f"{metric['text']}{metric['unit']}" if metric["text"] != "--" else "--"


def amb_typographic(c, clock, o):
    """Oversized numerals carry the screen, in two weights."""
    theme = c.theme
    _ticks(c, o)
    size = o["value-size"] + 26
    x = 8 + c.text_size("00", size, 0, 0)[0] / 2
    c.text(f"{clock['hour']:02}", 120 - x, 112 + o["title-offset"], size, theme["text"], tracking=0)
    c.text(f"{clock['minute']:02}", 120 + x, 112 + o["title-offset"], size, theme["primary"], tracking=0, weight=0 if c.crisp else 1)
    c.text(clock["date"], 120, 158, o["label-size"] + 1, theme["quiet"], tracking=o["tracking"], weight=1, max_width=140)


def amb_solar(c, clock, o):
    """The daylight arc, with the sun where HA says it is."""
    theme = c.theme
    sun = clock.get("sun")
    radius = o["gauge-radius"]
    c.arc(120, 125, radius, -120, 120, theme["grid"], o["track-width"])
    if sun and sun["progress"] is not None and sun["above"]:
        end = -120 + 240 * sun["progress"]
        c.arc(120, 125, radius, -120, end, theme["primary"], o["gauge-width"], under=theme["grid"])
        c.disc(*polar(120, 125, radius, end), 6, theme["secondary"], None, 1, theme["grid"])
    _big_time(c, clock, o, y=122)
    text = f"SUNSET {sun['setting']} · DAWN {sun['rising']}" if sun else "NO SUN DATA"
    c.text(text, 120, 149, o["label-size"], theme["quiet"], tracking=1, weight=1, max_width=150)


def amb_orbital(c, clock, o):
    """The hands become planets on two slow tracks."""
    theme = c.theme
    outer, inner = o["gauge-radius"], o["gauge-radius"] - 20
    c.ring(120, 119, outer, theme["quiet"])
    c.ring(120, 119, inner, theme["grid"])
    c.disc(*polar(120, 119, outer, clock["minute"] * 6), 7, theme["primary"], None, 1)
    c.disc(*polar(120, 119, inner, (clock["hour"] % 12 + clock["minute"] / 60) * 30), 4, theme["secondary"], None, 1)
    _big_time(c, clock, o, y=118, size=min(o["value-size"], 30))
    c.text(clock["date"], 120, 140, o["label-size"], theme["quiet"], tracking=1, weight=1, max_width=inner * 2 - 20)


def amb_status(c, clock, o):
    """Time first, with the house summed up in three small complications."""
    theme = c.theme
    _big_time(c, clock, o, y=84)
    weather = clock.get("weather")
    if weather:
        c.icon(WEATHER_ICONS.get(weather["state"], "mdi:weather-partly-cloudy"), 96, 112, 14, theme["primary"])
        c.text(weather["temperature"], 108, 112, o["label-size"] + 2, theme["secondary"], align="start", tracking=0, weight=1)
    c.text(clock["date"], 120, 124, o["label-size"], theme["quiet"], tracking=1, weight=1, max_width=150)
    for (x, y), metric in zip(((72, 154), (120, 164), (168, 154)), _metrics(clock, 3)):
        fill = theme["bg"] if c.crisp else theme["surface"]
        c.disc(x, y, 22, fill, theme["quiet"])
        c.text(metric["label"], x, y - 8, 6, theme["primary"], fill, tracking=0, weight=1, max_width=36)
        c.text(_reading(metric), x, y + 5, 8, theme["text"], fill, tracking=0, weight=1, max_width=38)


def wat_contour(c, clock, o):
    """Numerals follow the edge, lit up to the current hour."""
    theme = c.theme
    current = clock["hour"] % 12 or 12
    for index, numeral in enumerate((12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)):
        x, y = polar(120, 106, o["gauge-radius"], index * 30)
        strong = index % 3 == 0
        lit = numeral == 12 and current == 12 or numeral <= current and numeral != 12
        c.text(numeral, x, y, 19 if strong else 12, theme["primary"] if lit else theme["quiet"], tracking=0, weight=1 if strong else 0)
    _big_time(c, clock, o, y=102, size=min(o["value-size"], 30))
    c.text(clock["date"], 120, 124, o["label-size"] + 1, theme["secondary"], tracking=1, weight=1, max_width=90)


def wat_modular(c, clock, o):
    """Time and a disciplined stack of real complications."""
    theme = c.theme
    c.text(_time(clock), 172, 52, o["value-size"] - 8, theme["text"], align="end", tracking=0, weight=1)
    c.text(clock["date"], 62, 52, o["label-size"] + 1, theme["primary"], align="start", tracking=0, weight=1, max_width=62)
    first, second, third = _metrics(clock, 3)
    fill = theme["bg"] if c.crisp else theme["surface"]
    under = None if c.crisp else fill
    c.pill(120, 95, 150, 48, under, theme["quiet"], 1, radius=12)
    c.text(first["label"].upper(), 58, 84, 6, theme["quiet"], under, align="start", tracking=1, weight=1, max_width=124)
    c.text(_reading(first), 58, 103, 12, theme["text"], under, align="start", tracking=0, weight=1, max_width=124)
    for x, metric in ((81, second), (159, third)):
        c.pill(x, 151, 72, 50, under, theme["quiet"], 1, radius=12)
        c.text(_reading(metric), x, 146, 13, theme["text"], under, tracking=0, weight=1, max_width=62)
        c.text(metric["label"].upper(), x, 165, 6, theme["primary"], under, tracking=0, weight=1, max_width=62)


def wat_palette(c, clock, o):
    """Stacked bands fill as the day passes: hour, minute, weekday and month."""
    theme = c.theme
    fractions = (
        (clock["hour"] + clock["minute"] / 60) / 24, clock["minute"] / 60,
        clock["weekday"] / 7, clock["day"] / clock["days_in_month"],
    )
    width = o["gauge-width"] + 4
    for index, fraction in enumerate(fractions):
        radius = o["gauge-radius"] + 12 - index * (width + 4)
        c.arc(120, 110, radius, -115, 115, theme["grid"], width)
        if fraction > 0:
            colour = theme["secondary"] if index % 2 else theme["primary"]
            c.arc(120, 110, radius, -115, -115 + 230 * fraction, colour, width, under=theme["grid"])
    size = max(18, o["value-size"] - 8)
    gap = c.text_size("00", size, 0, 0)[0] / 2 + 2
    c.text(f"{clock['hour']:02}", 120 - gap, 112, size, theme["text"], tracking=0)
    c.text(f"{clock['minute']:02}", 120 + gap, 112, size, theme["primary"], tracking=0, weight=1)
    c.text(clock["weekday_name"], 120, 170, o["label-size"] + 1, theme["secondary"], tracking=2, weight=1, max_width=110)


def wat_rings(c, clock, o):
    """Three bold rings fill towards each metric's maximum; no maximum, no claim of progress."""
    theme = c.theme
    width = o["gauge-width"] + 3
    colours = (theme["primary"], theme["secondary"], theme["text"])
    metrics = _metrics(clock, 3)
    for index, metric in enumerate(metrics):
        radius = 62 - index * (width + 5)
        c.arc(100, 108, radius, -180, 180, theme["grid"], width)
        if metric["percent"]:
            c.arc(100, 108, radius, -180, -180 + 360 * metric["percent"] / 100, colours[index], width, cap=True, under=theme["grid"])
        y = 72 + index * 36
        c.text(metric["label"].upper(), 188, y - 7, 6, theme["quiet"], tracking=0, weight=1, max_width=46)
        c.text(_reading(metric), 188, y + 6, 11, theme["text"], tracking=0, weight=1, max_width=46)
    c.text(_time(clock), 100, 108, 11, theme["text"], tracking=0, weight=1)


def wat_solar(c, clock, o):
    """A horizon and a moving light field, positioned from the real sun."""
    theme = c.theme
    sun = clock.get("sun")
    if sun and sun["progress"] is not None:
        t = sun["progress"]
        x = 33 + 174 * t
        lift = 4 * t * (1 - t) * 46
        y = 132 - lift if sun["above"] else 132 + lift
        if c.crisp:
            flat = []
            for index in range(0, 360, 6):
                flat.extend((*polar(x, y, 10, index), *polar(x, y, 58, index)))
            c.lines(flat, c.tint(0.4))
            c.disc(x, y, 6, theme["bg"], theme["secondary"])
        else:
            for radius, amount in ((70, 0.06), (52, 0.1), (36, 0.16), (22, 0.26)):
                c.disc(x, y, radius, c.tint(amount), None, 1)
            c.disc(x, y, 6, theme["secondary"], None, 1, c.tint(0.26))
    c.path([(33 + 174 * step / 24, 132 - 4 * (step / 24) * (1 - step / 24) * 46) for step in range(25)], theme["secondary"])
    _big_time(c, clock, o, y=118)
    text = f"SUNSET {sun['setting']}" if sun and sun["above"] else f"SUNRISE {sun['rising']}" if sun else "NO SUN DATA"
    c.text(text, 120, 151, o["label-size"] + 1, theme["primary"], tracking=1, weight=1, max_width=130)


def wat_reflections(c, clock, o):
    """Machined metal. In Crisp the same sunburst is a line fan, and the moiré is the point."""
    theme = c.theme
    cy = 108
    if c.crisp:
        flat = []
        for angle in range(0, 360, 3):
            flat.extend((*polar(120, cy, 44, angle), *polar(120, cy, 92, angle)))
        c.lines(flat, c.tint(0.5))
        for radius in range(30, 43, 2):
            c.ring(120, cy, radius, theme["quiet"])
        c.disc(120, cy, 28, theme["bg"], theme["quiet"])
        size = min(o["value-size"], 16)
        c.text(f"{clock['hour']:02}", 120, cy - 8, size, theme["text"], tracking=2)
        c.text(f"{clock['minute']:02}", 120, cy + 10, size, theme["primary"], tracking=2)
        c.pill(120, 170, 74, 14, theme["bg"], None, radius=3)
        c.text(clock["date"], 120, 170, o["label-size"], theme["secondary"], tracking=1, weight=1, max_width=70)
    else:
        for index in range(18):
            amount = 0.08 + (index % 4) * 0.06
            colour = theme["secondary"] if index % 3 == 0 else theme["primary"]
            middle = index * 20
            c.poly(
                [(120, cy), *(polar(120, cy, 90, middle - 7 + 14 * step / 4) for step in range(5))],
                c.tint(amount, colour),
            )
        c.disc(120, cy, 48, c.tint(0.3, theme["text"]), None, 1, theme["bg"])
        c.disc(120, cy, 40, c.tint(0.14, theme["text"]), None, 1, c.tint(0.3, theme["text"]))
        under = c.tint(0.14, theme["text"])
        c.text(_time(clock), 120, cy - 3, min(o["value-size"], 26), theme["text"], under, tracking=0, weight=1)
        c.text(clock["date"], 120, cy + 18, o["label-size"], theme["secondary"], under, tracking=1, weight=1, max_width=66)


def _plot(series, x, y, width, height, low=None, high=None):
    """Scale a series into a rectangle. Returns points; an empty series plots nothing."""
    if not series:
        return []
    low = min(series) if low is None else low
    high = max(series) if high is None else high
    span = (high - low) or 1
    step = width / max(1, len(series) - 1)
    return [(x + index * step, y + height - (value - low) * height / span) for index, value in enumerate(series)]


def _primary_text(c, metric, y, size, o):
    c.text(_reading(metric), 120, y, size, c.theme["text"], tracking=0, weight=1, max_width=130)
    c.text(metric["label"].upper(), 120, y + size // 2 + 8, o["label-size"], c.theme["primary"], tracking=1, weight=1, max_width=130)


def dat_area(c, clock, o):
    """A filled trace of the recorded history, with its real range."""
    theme = c.theme
    metric = _metrics(clock, 1)[0]
    flat = []
    for index in range(5):
        y = 62 + index * 27
        flat.extend((45, y, 195, y))
    c.lines(flat, theme["grid"])
    points = _plot(metric["series"], 43, 92, 154, 72)
    if len(points) > 1:
        c.surface([*points, (197, 176), (43, 176)], c.tint(0.2), theme["primary"], hatch=c.tint(0.5))
    else:
        c.text("NO HISTORY", 120, 150, 7, theme["quiet"], tracking=1, weight=1)
    _primary_text(c, metric, 78, o["value-size"] - 6, o)


def dat_radar(c, clock, o):
    """Each metric gets a spoke, scaled by its own maximum."""
    theme = c.theme
    metrics = list(clock.get("metrics", []))
    cy = 112
    for radius in (24, 42, 61):
        c.ring(120, cy, radius, theme["grid"])
    count = max(3, len(metrics))
    points = []
    for index in range(count):
        c.line(120, cy, *polar(120, cy, 61, index * 360 / count), theme["grid"])
    for index, metric in enumerate(metrics):
        fraction = (metric["percent"] or 0) / 100
        points.append(polar(120, cy, 6 + 55 * fraction, index * 360 / count))
    if len(points) >= 3:
        c.surface(points, c.tint(0.2), theme["primary"], hatch=c.tint(0.5))
    for index, metric in enumerate(metrics):
        x, y = polar(120, cy, 76, index * 360 / count)
        c.text(metric["label"][:6].upper(), x, y, 6, theme["quiet"], tracking=0, weight=1, max_width=36)
    known = sum(1 for metric in metrics if metric["percent"] is not None)
    c.text(f"{known} SIGNALS" if metrics else "NO METRICS", 120, 180, o["label-size"], theme["primary"], tracking=1, weight=1)


def dat_bands(c, clock, o):
    """Nested tracks: current level, with the recorded range drawn behind it."""
    theme = c.theme
    colours = (theme["primary"], theme["secondary"], theme["quiet"])
    metrics = _metrics(clock, 3)
    for index, metric in enumerate(metrics):
        radius = o["gauge-radius"] - index * (o["gauge-width"] + 5)
        c.arc(120, 119, radius, -130, 130, theme["grid"], o["gauge-width"] + 2)
        if metric["percent"]:
            c.arc(120, 119, radius, -130, -130 + 260 * metric["percent"] / 100, colours[index], o["gauge-width"], cap=True, under=theme["grid"])
    _primary_text(c, metrics[0], 116, min(o["value-size"], 24), o)


def dat_spark(c, clock, o):
    """One dominant sparkline over a row of supporting values."""
    theme = c.theme
    metrics = _metrics(clock, 4)
    flat = []
    for index in range(3):
        y = 62 + index * 27
        flat.extend((45, y, 195, y))
    c.lines(flat, theme["grid"])
    points = _plot(metrics[0]["series"], 46, 62, 148, 54)
    if len(points) > 1:
        c.path(points, theme["primary"])
    else:
        c.text("NO HISTORY", 120, 88, 7, theme["quiet"], tracking=1, weight=1)
    c.text(_reading(metrics[0]), 120, 134, min(o["value-size"], 22), theme["text"], tracking=0, weight=1, max_width=130)
    for x, metric in ((65, metrics[1]), (120, metrics[2]), (175, metrics[3])):
        c.text(_reading(metric), x, 166, 10, theme["text"], tracking=0, weight=1, max_width=50)
        c.text(metric["label"].upper(), x, 178, 5, theme["quiet"], tracking=0, weight=1, max_width=50)


FACES = {
    "AMB-TYPOGRAPHIC": amb_typographic, "AMB-SOLAR": amb_solar, "AMB-ORBITAL": amb_orbital, "AMB-STATUS": amb_status,
    "WAT-CONTOUR": wat_contour, "WAT-MODULAR": wat_modular, "WAT-PALETTE": wat_palette, "WAT-RINGS": wat_rings,
    "WAT-SOLAR": wat_solar, "WAT-REFLECTIONS": wat_reflections,
    "DAT-AREA": dat_area, "DAT-RADAR": dat_radar, "DAT-BANDS": dat_bands, "DAT-SPARK": dat_spark,
}


def face_layout(c: Canvas, view: dict, o: dict) -> list[dict]:
    clock = view.get("_clock")
    if not clock:
        c.text("TIME UNAVAILABLE", 120, 118, 9, c.theme["text"], tracking=1, max_width=140)
        return []
    FACES[view["style"]](c, clock, o)
    items = view.get("items", [])
    if not items:
        return []
    # A face can still front a page: its current destination stays reachable by touch.
    selected = items[view.get("selected", 0) % len(items)]
    c.text(selected["label"], 120, 192, 7, c.theme["primary"], tracking=1, weight=1, max_width=110)
    return [{"id": selected["id"], "x": 120, "y": 190, "r": 9}]
