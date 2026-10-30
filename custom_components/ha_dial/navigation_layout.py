"""Atlas navigation geometry; the renderers receive resolved coordinates only."""

from math import cos, pi, sin


def point(radius, angle, cx=120, cy=120):
    angle = (angle - 90) * pi / 180
    return round(cx + cos(angle) * radius), round(cy + sin(angle) * radius)


def navigation_layout(view, items, selected, options, theme):
    style = view.get("style", "NAV-ORBIT")
    count = len(items)
    index = selected % max(1, count)
    visible = list(range(count))
    extra = []
    title_y, label_y, footer_y, cog_y = 108, 128, 158, 77
    positions = [
        point(options["orbit-radius"], n * 360 / max(1, count)) for n in visible
    ]
    if style == "NAV-ROLODEX":
        visible = (
            [(index + offset) % count for offset in (-1, 0, 1)]
            if count > 2
            else visible
        )
        positions = [(62, 72 + slot * 40) for slot in range(len(visible))]
        title_y, label_y, footer_y, cog_y = 183, 0, 212, 27
    elif style == "NAV-PETALS":
        positions = [point(72, n * 360 / max(1, count), cy=112) for n in visible]
        for n in visible:
            angle = n * 360 / max(1, count)
            spread = min(32, 160 / max(1, count))
            ink = theme["primary"] if n == selected else theme["grid"]
            extra.append(
                {
                    "op": "arc",
                    "x": 120,
                    "y": 112,
                    "r": 96,
                    "start": round(angle - spread),
                    "end": round(angle + spread),
                    "stroke": ink,
                    "width": 2,
                }
            )
            for edge in (angle - spread, angle + spread):
                x, y = point(96, edge, cy=112)
                ix, iy = point(44, edge, cy=112)
                extra.append(
                    {"op": "line", "x1": ix, "y1": iy, "x2": x, "y2": y, "stroke": ink}
                )
        footer_y = 212
    elif style == "NAV-CONSTELLATION":
        positions = [
            point(76 if n % 2 else 88, n * 360 / max(1, count) + 15) for n in visible
        ]
        for slot, (x, y) in enumerate(positions):
            nx, ny = positions[(slot + 1) % max(1, count)]
            extra.append(
                {
                    "op": "line",
                    "x1": x,
                    "y1": y,
                    "x2": nx,
                    "y2": ny,
                    "stroke": theme["grid"],
                }
            )
    elif style == "NAV-COMPASS":
        start = (index // 4) * 4
        visible = list(range(start, min(start + 4, count)))
        positions = [(120, 40), (200, 112), (120, 190), (40, 112)][: len(visible)]
    elif style == "NAV-RIBBON":
        visible = (
            [(index + offset) % count for offset in range(-2, 3)]
            if count > 4
            else visible
        )
        positions = [(50 + 35 * slot, 155 - 23 * slot) for slot in range(len(visible))]
        title_y, label_y, footer_y, cog_y = 30, 183, 212, 60
        for slot in range(len(positions) - 1):
            x, y = positions[slot]
            nx, ny = positions[slot + 1]
            extra.append(
                {
                    "op": "line",
                    "x1": x,
                    "y1": y,
                    "x2": nx,
                    "y2": ny,
                    "stroke": theme["quiet"],
                }
            )
    elif style == "NAV-BREADCRUMB":
        visible = [index] if count else []
        positions = [(120, 145)] if count else []
        title_y, label_y, footer_y, cog_y = 106, 183, 212, 30
        ancestors = view.get("breadcrumbs", [])
        if ancestors:
            extra.append(
                {
                    "op": "mask",
                    "x": 120,
                    "y": 70,
                    "text": ancestors[-1],
                    "size": 8,
                    "colour": theme["quiet"],
                }
            )
        for y, width in ((70, 140), (106, 120), (145, 96)):
            extra.append(
                {
                    "op": "line",
                    "x1": 120 - width // 2,
                    "y1": y + 15,
                    "x2": 120 + width // 2,
                    "y2": y + 15,
                    "stroke": theme["grid"],
                }
            )
    return (
        [(n, items[n], *positions[slot]) for slot, n in enumerate(visible)],
        extra,
        {"title": title_y, "label": label_y, "footer": footer_y, "cog": cog_y},
    )
