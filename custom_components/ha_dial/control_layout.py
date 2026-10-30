"""Atlas instrument/editorial control geometry resolved entirely in HA."""

from .assets import _number_mask


def control_layout(view: dict, theme: dict) -> tuple[list, list]:
    available = view.get("available", True)
    value = view.get("value", 0)
    domain = view.get("domain", "sensor")
    editorial = view.get("style", "").endswith("-EDITORIAL")
    continuous = view.get("continuous", False)
    options = view.get("options", [])
    if domain in {"select", "input_select"} and options:
        main = options[max(0, min(len(options) - 1, round(value)))]
    elif (
        continuous
        or domain in {"sensor", "number", "input_number"}
        and view.get("numeric_value", True)
    ):
        main = f"{value:g}"
    else:
        main = str(view.get("state", "--")).replace("_", " ").upper()
    if domain == "scene":
        main = "ACTIVATE"
    elif domain in {"button", "input_button"}:
        main = "PRESS"
    if not available:
        main = "--"
    elements = []

    def text(value, y, size, colour=None):
        elements.append(
            {
                "op": "mask",
                "x": 120,
                "y": y,
                "text": str(value),
                "size": size,
                "colour": colour or theme["text"],
            }
        )

    text(view.get("title", domain), 30, view.get("_font_size", 11))
    elements.append(
        {
            "op": "icon",
            "x": 120,
            "y": 79,
            "icon": view.get("icon", "mdi:information"),
            "size": view.get("_icon_size", 18),
            "colour": theme["primary"],
        }
    )
    if not editorial:
        elements.append(
            {
                "op": "arc",
                "x": 120,
                "y": 120,
                "r": 74,
                "start": -125,
                "end": 125,
                "stroke": theme["grid"],
                "width": 5,
            }
        )
        if continuous:
            minimum, maximum = view.get("minimum", 0), view.get("maximum", 100)
            percent = max(
                0, min(100, (value - minimum) * 100 / max(0.001, maximum - minimum))
            )
            elements.append(
                {
                    "op": "gauge",
                    "value": round(percent),
                    "minimum": minimum,
                    "maximum": maximum,
                    "fill": theme["primary"],
                    "x": 120,
                    "y": 120,
                    "r": 74,
                    "start": -125,
                    "end": 125,
                    "stroke": theme["primary"],
                    "width": 3,
                }
            )
    precision = min(2, len(str(view.get("step", 1)).rstrip("0").partition(".")[2]))
    scale = 10**precision
    if (
        continuous
        and domain not in {"select", "input_select"}
        and max(abs(view.get("minimum", 0)), abs(view.get("maximum", 100))) * scale
        <= 999999
    ):
        elements.append(
            {
                "op": "number",
                "x": 120,
                "y": 115,
                "value": round(value * scale),
                "precision": precision,
                "characters": "0123456789.-",
                **_number_mask(24, view.get("_raster", "smooth"), True),
                "colour": theme["primary"] if view.get("pending") else theme["text"],
                "stroke": theme["primary"],
                "background": theme["bg"],
            }
        )
    else:
        text(main, 115, 24 if len(main) < 9 else 12)
    text(
        view.get("unit", "")
        if continuous or domain == "sensor"
        else domain.replace("_", " ").upper(),
        139,
        7,
        theme["secondary"],
    )
    if not view.get("confirmation"):
        text(
            "PENDING"
            if view.get("pending")
            else view.get("detail", view.get("state", "")),
            157,
            7,
            theme["quiet"],
        )
    regions = []
    if view.get("confirmation"):
        text(
            "CONFIRM " + str(view["confirmation"]).upper() + "?",
            157,
            7,
            theme["primary"],
        )
        actions = ["cancel", "confirm"]
    else:
        actions = view.get("actions", [])
        if domain in {"light", "switch"}:
            actions = ["control"]
        if not available:
            actions = []
    for index, action in enumerate(actions[:4]):
        x = round(120 + (index - (len(actions[:4]) - 1) / 2) * 42)
        elements.append(
            {
                "op": "circle",
                "x": x,
                "y": 183,
                "r": 19,
                "stroke": theme["primary"],
                "fill": theme["surface"],
            }
        )
        elements.append(
            {
                "op": "mask",
                "x": x,
                "y": 183,
                "text": action.replace("_", " ").upper(),
                "size": 7,
                "colour": theme["text"],
            }
        )
        regions.append({"id": action, "x": x, "y": 183, "r": 19})
    if view.get("confirmation"):
        text("TURN TO CANCEL", 55, 6, theme["secondary"])
    return elements, regions
