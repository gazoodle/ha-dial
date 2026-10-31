"""Control shapes: the same domain can read as a ring, big type, a column, segments or a tumbler.

Every shape carries a firmware-updated number and gauge, so rotary feedback stays immediate.
Domain graphics live in control_graphics.py.
"""

from .canvas import Canvas
from .control_graphics import GRAPHICS, NO_UNIT, gauge_ring, icon_name

ACTION_ICONS = {
    "open": "mdi:arrow-up", "close": "mdi:arrow-down", "stop": "mdi:stop", "play_pause": "mdi:play-pause",
    "previous": "mdi:skip-previous", "next": "mdi:skip-next", "mute": "mdi:volume-mute", "mode": "mdi:sync",
    "toggle": "mdi:power", "preset": "mdi:tune", "lock": "mdi:lock", "unlock": "mdi:lock-open", "disarm": "mdi:shield-off",
    "arm_home": "mdi:shield-home", "arm_away": "mdi:shield-lock", "arm_night": "mdi:shield-moon", "arm_vacation": "mdi:shield-airplane",
    "start": "mdi:play", "pause": "mdi:pause", "cancel": "mdi:close", "dock": "mdi:home-import-outline", "activate": "mdi:play",
    "press": "mdi:gesture-tap", "confirm": "mdi:check", "control": "mdi:power",
}


def readout(view: dict) -> str | None:
    """Text for a state that has no number; None means the number atlas should draw it."""
    domain = view.get("domain", "sensor")
    if not view.get("available", True):
        return "--"
    if domain == "scene":
        return "ACTIVATE"
    if domain in {"button", "input_button"}:
        return "PRESS"
    if domain == "switch":
        return "ON" if view.get("active") else "OFF"
    if domain in {"select", "input_select"} and view.get("options"):
        options = view["options"]
        return str(options[max(0, min(len(options) - 1, round(view.get("value", 0))))])
    if not view.get("position_known", True):
        return "--"
    if domain in {"light", "cover"} or view.get("continuous"):
        return None
    if domain in {"sensor", "number", "input_number"} and view.get("numeric_value", True):
        return f"{view.get('value', 0):g}"
    return str(view.get("state", "--")).replace("_", " ").upper()


def _precision(view: dict) -> int:
    step = str(view.get("step", 1))
    return min(2, len(step.rstrip("0").partition(".")[2])) if "." in step else 0


def number_width(c: Canvas, view: dict, size: int) -> int:
    """Rendered width of the digit atlas, which the firmware advances by whole cells."""
    return c.number_cell(min(size, 48)) * len(f"{view.get('value', 0):.{_precision(view)}f}")


def value_element(c: Canvas, view: dict, o: dict, x, y, size, under=None, max_width=150) -> None:
    """The main value: a digit atlas when rotary input can change it, otherwise plain text."""
    theme = c.theme
    text = readout(view)
    if text is not None:
        c.text(text, x, y, size if len(text) < 7 else max(12, size * 7 // max(7, len(text))), theme["text"], under, tracking=0, weight=1, max_width=max_width)
        return
    precision = _precision(view)
    scale = 10**precision
    value = view.get("value", 0)
    c.number(
        round(value * scale), x, y, min(size, 48), theme["primary"] if view.get("pending") else theme["text"], theme["primary"],
        extended=True, precision=precision, under=under,
    )


def percent_of(view: dict) -> float:
    low, high = view.get("minimum", 0), view.get("maximum", 100)
    return max(0, min(100, (view.get("value", 0) - low) * 100 / max(0.001, high - low)))


def local_gauge(c: Canvas, view: dict, x, y, radius, start, end, width=2, under=None) -> None:
    """A slim firmware-updated arc, so every shape responds immediately while turning."""
    if view.get("domain") in {"select", "input_select"} or not (view.get("continuous") or view.get("domain") in {"light", "cover"}):
        return
    c.gauge(x, y, radius, start, end, percent_of(view), c.theme["primary"], width, minimum=view.get("minimum", 0), maximum=view.get("maximum", 100), under=under)


def detail_text(view: dict) -> str:
    if view.get("pending"):
        return "PENDING"
    if not view.get("available", True):
        return "UNAVAILABLE"
    detail = str(view.get("detail", view.get("state", ""))).replace("_", " ").upper()
    # Sensors and selects report their state as detail; saying it twice wastes the line.
    return "" if detail == str(readout(view) or "").upper() else detail


def _lit(view: dict, count: int) -> int:
    return round(percent_of(view) * count / 100) if view.get("continuous") or view.get("domain") in {"light", "cover"} else 0


def _top_pill(c: Canvas, view: dict, o: dict) -> None:
    label = str(view.get("title", view.get("domain", ""))).upper()
    width = min(120, max(52, c.text_size(label, 7, 1, 1)[0] + 20))
    fill = c.tint(0.13)
    c.pill(120, 24, width, 18, None if c.crisp else fill, c.theme["primary"], 1)
    c.text(label, 120, 24, 7, c.theme["secondary"], None if c.crisp else fill, tracking=1, weight=1, max_width=width - 12)


def _instrument(c, view, o, name):
    GRAPHICS.get(name, gauge_ring)(c, view, o)
    unit = view.get("unit", "")
    if unit and name not in NO_UNIT:
        c.text(unit, 120, 141 + o["value-offset"], o["unit-size"], c.theme["primary"], tracking=1, weight=1)


def _editorial(c, view, o, name):
    """Type alone: a large left-set value against a rule, with no instrument around it."""
    theme = c.theme
    left, y = 44, 104 + o["value-offset"]
    c.icon(icon_name(view, o), left + o["selected-icon-size"] / 2, 60, o["selected-icon-size"], theme["primary"])
    c.text(str(view.get("title", "")).upper(), left, 60 + o["selected-icon-size"], max(7, o["font-size"] - 4), theme["secondary"], align="start", tracking=o["tracking"], weight=1, max_width=150)
    size = o["value-size"] + 12
    text = readout(view)
    if text is not None:
        c.text(text, left, y + 12, size, theme["text"], align="start", tracking=0, weight=1, max_width=154)
    else:
        width = number_width(c, view, size)
        value_element(c, view, o, left + width / 2, y + 12, size)
        c.text(view.get("unit", ""), left + width + 6, y + 22, o["unit-size"] + 2, theme["primary"], align="start", tracking=1, weight=1)
    rule = y + 12 + size / 2 + 8
    c.line(left, rule, 196, rule, theme["quiet"])
    c.text(detail_text(view), left, rule + 12 + o["detail-offset"], o["detail-size"], theme["quiet"], align="start", tracking=o["tracking"], weight=1, max_width=150)
    local_gauge(c, view, 120, 120, 106, -60, 60, 2)


def _column(c, view, o, name):
    """A vertical stack of segments beside the value."""
    theme = c.theme
    count, gap, width = o["bar-count"], o["bar-gap"], o["bar-width"]
    top, bottom = 52, 164
    height = (bottom - top - gap * (count - 1)) / count
    lit = _lit(view, count)
    left = 70 - width / 2 + 16
    for index in range(count):
        y = bottom - height / 2 - index * (height + gap)
        active = index < lit
        fill = theme["primary"] if active else theme["surface"]
        if c.crisp and not active:
            c.pill(left + width / 2, y, width, height, None, theme["grid"], 1, radius=0)
        else:
            c.pill(left + width / 2, y, width, height, fill, None, radius=0)
    x = left + width + (240 - left - width - 28) / 2
    c.icon(icon_name(view, o), x, 74, o["selected-icon-size"], theme["primary"])
    value_element(c, view, o, x, 112 + o["value-offset"], o["value-size"], max_width=round(2 * (214 - x)))
    c.text(view.get("unit", ""), x, 112 + o["value-offset"] + o["value-size"] // 2 + 7, o["unit-size"], theme["primary"], tracking=1, weight=1)
    c.text(detail_text(view), 120, (155 if view.get("actions") else 176) + o["detail-offset"], o["detail-size"], theme["quiet"], tracking=o["tracking"], weight=1, max_width=150)
    local_gauge(c, view, 120, 120, 106, -135, -45, o["selected-border"])


def _segment(c, view, o, name):
    """A broken ring: discrete steps, read at a glance."""
    theme = c.theme
    count, gap = o["bar-count"], o["bar-gap"] * 2
    radius, width = o["gauge-radius"] + 8, o["track-width"]
    sweep = 264
    each = (sweep - gap * (count - 1)) / count
    lit = _lit(view, count)
    for index in range(count):
        start = -132 + index * (each + gap)
        c.arc(120, 118, radius, start, start + each, theme["primary"] if index < lit else theme["grid"], max(2, width))
    local_gauge(c, view, 120, 118, radius - width - 3, -132, 132, max(1, o["gauge-width"] // 3))
    c.icon(icon_name(view, o), 120, 72, o["selected-icon-size"], theme["secondary"])
    value_element(c, view, o, 120, 116 + o["value-offset"], o["value-size"])
    c.text(view.get("unit", ""), 120, 116 + o["value-offset"] + o["value-size"] // 2 + 7, o["unit-size"], theme["primary"], tracking=1, weight=1)
    c.text(detail_text(view), 120, 156 + o["detail-offset"], o["detail-size"], theme["quiet"], tracking=o["tracking"], weight=1, max_width=120)


def _tumbler(c, view, o, name):
    """A rolling wheel: the neighbouring values sit above and below the selection."""
    theme = c.theme
    width, height = o["row-width"], o["row-height"] + 16
    y = 106 + o["value-offset"]
    fill = c.tint(0.16)
    c.pill(120, y, width, height, None if c.crisp else fill, theme["primary"], o["selected-border"], radius=6)
    options = view.get("options") or []
    if view.get("domain") in {"select", "input_select"} and options:
        index = max(0, min(len(options) - 1, round(view.get("value", 0))))
        above = options[index - 1] if index else ""
        below = options[index + 1] if index + 1 < len(options) else ""
        c.text(options[index], 120, y, min(o["value-size"], 22), theme["text"], None if c.crisp else fill, tracking=0, weight=1, max_width=width - 16)
    else:
        step = view.get("step", 1)
        value = view.get("value", 0)
        low, high = view.get("minimum", 0), view.get("maximum", 100)
        above = f"{value + step:g}" if readout(view) is None and value + step <= high else ""
        below = f"{value - step:g}" if readout(view) is None and value - step >= low else ""
        value_element(c, view, o, 120, y, o["value-size"], None if c.crisp else fill)
    for text, offset, size in ((above, -(height / 2 + 13), 12), (below, height / 2 + 13, 12)):
        c.text(text, 120, y + offset, size, theme["quiet"], tracking=0, max_width=width - 30)
    c.text(view.get("unit", ""), 120 + width / 2 - 14, y, o["unit-size"], theme["primary"], None if c.crisp else fill, tracking=1, weight=1)
    c.icon(icon_name(view, o), 120, 47, o["selected-icon-size"] - 5, theme["secondary"])
    c.text(detail_text(view), 120, (158 if view.get("actions") else 166) + o["detail-offset"], o["detail-size"], theme["quiet"], tracking=o["tracking"], weight=1, max_width=130)
    local_gauge(c, view, 120, 120, 106, 60, 120, 2)


SHAPES = {"INSTRUMENT": _instrument, "EDITORIAL": _editorial, "COLUMN": _column, "SEGMENT": _segment, "TUMBLER": _tumbler}


def _actions(c: Canvas, view: dict, o: dict) -> tuple[list, list]:
    """Icon buttons, which unlike labels can't overflow their circles."""
    if view.get("confirmation"):
        actions = ["cancel", "confirm"]
    elif not view.get("available", True):
        actions = []
    else:
        actions = [action for action in view.get("actions", []) if action != "control"]
    actions = actions[:4]
    regions = []
    size, spacing = o["action-size"], 2 * o["action-size"] + o["action-gap"]
    y = 183 + o["action-offset"]
    for index, action in enumerate(actions):
        x = round(120 + (index - (len(actions) - 1) / 2) * spacing)
        fill = c.theme["bg"] if c.crisp else c.theme["surface"]
        c.disc(x, y, size, fill, c.theme["primary"], 1)
        c.icon(ACTION_ICONS.get(action, "mdi:gesture-tap"), x, y, round(size * 1.1), c.theme["text"], fill)
        regions.append({"id": action, "x": x, "y": y, "r": max(14, size)})
    return actions, regions


def control_layout(c: Canvas, view: dict, o: dict) -> list[dict]:
    view = {"domain": "light", **view}
    style = view.get("style", "")
    shape = style.rsplit("-", 1)[-1] if style.count("-") >= 2 else "INSTRUMENT"
    name = style.split("-")[1] if style.count("-") >= 2 else "LIGHT"
    theme = c.theme
    if shape not in SHAPES:
        shape = "INSTRUMENT"
    if shape != "EDITORIAL":
        _top_pill(c, view, o)
    SHAPES[shape](c, view, o, name)
    if view.get("confirmation"):
        c.text("CONFIRM " + str(view["confirmation"]).replace("_", " ").upper() + "?", 120, 161, o["detail-size"], theme["primary"], tracking=1, weight=1, max_width=150)
        c.text("TURN TO CANCEL", 120, 40, 6, theme["secondary"], tracking=1)
    _, regions = _actions(c, view, o)
    if view.get("domain") in {"light", "switch"} or (view.get("domain") == "cover" and "stop" in view.get("actions", [])):
        regions.append({"id": "control", "x": 120, "y": 116, "r": 30})
    return regions

