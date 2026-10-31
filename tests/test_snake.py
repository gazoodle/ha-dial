"""The Snake navigation: its path reads in snake order, and no setting can produce a scene the Dial rejects."""

import json
from itertools import pairwise, product
from math import hypot

import pytest

ITEMS = [{"id": f"p{n}", "label": f"Page {n}", "icon": "mdi:folder"} for n in range(40)]


def view(count=9, selected=4, raster="smooth", **settings):
    return {"kind": "menu", "id": "home", "title": "Home", "style": "NAV-SNAKE", "back": True, "items": ITEMS[:count], "selected": selected, "appearance": {"raster": raster, **settings}}


def arranged(dial, count=9, selected=4, **settings):
    appearance, snake_path = dial.load("appearance"), dial.load("snake_path")
    options = appearance.appearance({"appearance": settings})
    return snake_path.arrange(count, selected, options, options["icon-size"] // 2 + options["item-padding"])


def test_rows_alternate_direction_from_top_to_bottom(dial):
    icons = arranged(dial).icons
    assert [n for n, _, _ in icons] == list(range(9))
    rows = [icons[:3], icons[3:6], icons[6:]]
    tops = [row[0][2] for row in rows]
    assert tops == sorted(tops) and len(set(tops)) == 3
    assert all(len({y for _, _, y in row}) == 1 for row in rows)
    assert rows[0][0][1] < rows[0][2][1], "the first row runs left to right"
    assert rows[1][0][1] > rows[1][2][1], "the second runs right to left"
    assert rows[2][0][1] < rows[2][2][1], "the third runs left to right again"


@pytest.mark.parametrize("per_row", [2, 3, 4])
def test_per_row_sets_how_many_share_a_row(dial, per_row):
    icons = arranged(dial, count=per_row * 2, selected=0, **{"snake-per-row": per_row}).icons
    assert sum(y == icons[0][2] for _, _, y in icons) == per_row


def test_turn_extension_projects_the_turn_further_out(dial):
    def reach(extension):
        arcs = arranged(dial, **{"snake-extension": extension}).arcs
        return max(abs(x - 120) for x, *_ in arcs)

    assert reach(20) == reach(10) + 10


def test_twist_turns_the_whole_snake_as_one(dial):
    def icons(twist):
        return arranged(dial, count=6, selected=0, **{"snake-twist": twist}).icons

    def distances(placed):
        return [hypot(a[1] - b[1], a[2] - b[2]) for a, b in pairwise(placed)]

    # It may shrink to stay clear of the label, but only ever evenly.
    level, twisted = distances(icons(0)), distances(icons(35))
    ratios = [after / before for before, after in zip(level, twisted)]
    assert max(ratios) - min(ratios) < 0.01 and 0.8 < min(ratios) <= 1
    assert icons(35) != icons(0)


def test_along_path_spaces_icons_evenly_and_puts_them_on_the_returns(dial):
    settings = {"snake-placement": "along path", "snake-spacing": 44}
    icons = arranged(dial, count=9, selected=0, **settings).icons
    rows = {round(y) for _, _, y in icons}
    assert len(rows) > 3, "an icon on a turn sits between the rows"


def test_only_the_travelled_part_is_lit(dial):
    snake = arranged(dial, selected=4)
    assert any(line[4] for line in snake.lines) and not all(line[4] for line in snake.lines)
    assert not any(line[4] for line in arranged(dial, selected=0).lines)


@pytest.mark.parametrize("selected", range(40))
def test_a_long_snake_scrolls_with_the_selection_and_leaves_a_tail(dial, selected):
    snake = arranged(dial, count=40, selected=selected)
    shown = [n for n, _, _ in snake.icons]
    assert selected in shown and shown == list(range(shown[0], shown[-1] + 1))
    assert len(shown) <= 12
    assert 0 < shown[0] or shown[-1] == 39 or selected < 9


def test_every_setting_at_its_limits_gives_a_scene_the_dial_accepts(dial):
    scene, appearance = dial.load("scene"), dial.load("appearance")
    limits = {name: appearance.NUMBERS[name][2:4] for name in ("snake-row-length", "snake-turn", "snake-extension", "snake-twist")}
    names = list(limits)
    for values, (edge, width), placement, count, raster in product(
        product(*limits.values()),
        (("single", 1), ("single", 4), ("double", 1), ("double", 4)),
        ("per row", "along path"),
        (1, 12, 40),
        ("smooth", "crisp"),
    ):
        settings = {**dict(zip(names, values)), "snake-edge": edge, "snake-width": width, "snake-placement": placement}
        resolved = scene.compile_scene(view(count, min(4, count - 1), raster, **settings))
        assert len(resolved["elements"]) <= 64, settings
        assert len(resolved["regions"]) <= 16, settings
        assert len(json.dumps({"scene": resolved, "previous": resolved}, separators=(",", ":"))) <= scene.MAX_VIEW_BYTES, settings
        for element in resolved["elements"]:
            if element["op"] == "arc":
                assert -360 <= element["start"] < element["end"] <= 360, (settings, element)
                assert 0 <= element["x"] < 240 and 0 <= element["y"] < 240, (settings, element)
                assert 0 < element["r"] <= 120, (settings, element)
            elif element["op"] == "circle":
                assert 0 <= element["x"] < 240 and 0 <= element["y"] < 240, (settings, element)
            elif element["op"] == "mask":
                assert 0 <= element["x"] - element["width"] // 2 and element["x"] + element["width"] // 2 < 240, (settings, element)


def test_custom_colours_reach_the_line(dial):
    scene = dial.load("scene")
    resolved = scene.compile_scene(view(9, 4, "smooth", **{"snake-line": "#123456", "snake-travelled": "#654321"}))
    strokes = {element.get("stroke") for element in resolved["elements"]}
    assert {"#123456", "#654321"} <= strokes
    unlit = scene.compile_scene(view(9, 4, "smooth", **{"snake-line": "#123456", "snake-travelled": "#654321", "snake-lit": False}))
    assert "#654321" not in {element.get("stroke") for element in unlit["elements"]}
