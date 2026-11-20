"""The checks that make a style real: its settings work, it looks distinct and its text fits."""

import json
import sys
from itertools import combinations, product
from math import hypot

import pytest

ITEMS = [
    {"id": name.lower(), "label": name, "icon": icon, "children": []}
    for name, icon in (
        ("Building", "mdi:office-building"),
        ("Floors", "mdi:layers"),
        ("Rooms", "mdi:floor-plan"),
        ("Lights", "mdi:lightbulb"),
        ("A very long destination name", "mdi:thermometer"),
        ("Media", "mdi:play-circle"),
    )
]
CLOCK = {
    "hour": 10, "minute": 9, "second": 37, "day": 27, "date": "MON 27 OCT", "moon": "waxing_crescent",
    "reserve": 40, "zones": [("UTC", "10:09"), ("NEW YORK", "06:09"), ("TOKYO", "19:09"), ("SYDNEY", "21:09")],
    "weekday": 1, "days_in_month": 31, "weekday_name": "MONDAY", "weather": {"state": "sunny", "temperature": "17°C"},
    "sun": {"above": True, "rising": "07:18", "setting": "17:42", "progress": 0.34},
    "metrics": [
        {"label": f"Metric {n}", "value": 40 + n, "text": str(40 + n), "unit": "%", "percent": 40 + n, "series": [10, 30, 20, 50, 40]}
        for n in range(6)
    ],
}
LEVEL = {"value": 62, "continuous": True, "unit": "%", "detail": "Warm white", "state": "on", "active": True, "available": True, "icon": "mdi:lightbulb"}
SHAPES = ("INSTRUMENT", "EDITORIAL", "COLUMN", "SEGMENT", "TUMBLER")


def views(catalogue):
    for style in sorted(catalogue.NAV_STYLES):
        yield {"kind": "menu", "id": "home", "title": "Example page", "style": style, "back": True, "breadcrumbs": ["Campus", "First floor"], "items": ITEMS, "selected": 2 if style == "NAV-SNAKE" else 0}
    for style in sorted(catalogue.FACE_STYLES):
        yield {"kind": "menu", "id": "clock", "title": "HA DIAL", "style": style, "items": [], "back": True, "_clock": CLOCK}
    for shape in SHAPES:
        yield {"kind": "control", "id": "c", "domain": "light", "title": "Example lamp", "style": f"CTL-LIGHT-{shape}", "back": True, "actions": ["toggle", "stop"], **LEVEL}


@pytest.mark.parametrize("raster", ["smooth", "crisp"])
def test_every_declared_setting_changes_the_scene(dial, raster):
    scene, appearance = dial.load("scene"), dial.load("appearance")
    dead = []
    for view in views(dial.load("catalogue")):
        for setting in appearance.style_settings(view["style"], raster):
            if setting == "raster" or setting in appearance.FRAME_SETTINGS:
                continue
            if setting in appearance.NUMBERS:
                low, high = appearance.NUMBERS[setting][2:4]
                values = (low, high)
            elif setting in appearance.TOGGLES:
                values = (True, False)
            else:
                values = appearance.CHOICES[setting][2][:2]
            needs = dict([appearance.REQUIRES[setting]]) if setting in appearance.REQUIRES else {}
            first, second = (
                scene.compile_scene({**view, "appearance": {"raster": raster, "tick-ring": True, "ring-double": True, **needs, setting: value}}) for value in values
            )
            if first == second:
                dead.append((view["style"], setting))
    assert not dead, dead


def test_settings_show_only_for_declaring_styles_and_validate(dial):
    appearance = dial.load("appearance")
    known = {*appearance.NUMBERS, *appearance.TOGGLES, *appearance.CHOICES}
    for style, settings in appearance.STYLE_SETTINGS.items():
        assert set(settings) <= known, style
    assert appearance.style_settings("CHR-TRICOMPAX") != appearance.style_settings("NAV-PETALS")
    assert "hub-radius" not in appearance.style_settings("NAV-ROLODEX")
    with pytest.raises(ValueError):
        appearance.appearance({"appearance": {"row-gap": 99}})
    with pytest.raises(ValueError):
        appearance.appearance({"appearance": {"chrome-style": "wobbly"}})


@pytest.mark.parametrize("raster", ["smooth", "crisp"])
def test_styles_for_a_domain_are_all_different(dial, raster):
    catalogue, scene = dial.load("catalogue"), dial.load("scene")
    for domain in catalogue.CONTROL_TYPES:
        styles = sorted(catalogue.control_styles(domain))
        drawings = {
            style: json.dumps(
                scene.compile_scene(
                    {"kind": "control", "id": "c", "domain": domain, "title": "Example", "style": style, "appearance": {"raster": raster}, "_clock": CLOCK, **LEVEL}
                )["elements"]
            )
            for style in styles
        }
        for first, second in combinations(styles, 2):
            assert drawings[first] != drawings[second], (domain, first, second)
    menus = [
        json.dumps(scene.compile_scene({**view, "appearance": {"raster": raster}})["elements"])
        for view in views(catalogue)
        if view["kind"] == "menu"
    ]
    assert len(set(menus)) == len(menus)


@pytest.mark.parametrize("raster", ["smooth", "crisp"])
def test_scenes_fit_the_display_and_transport(dial, raster):
    scene = dial.load("scene")
    for view in views(dial.load("catalogue")):
        resolved = scene.compile_scene({**view, "appearance": {"raster": raster}})
        assert len(resolved["elements"]) <= 64, view["style"]
        assert len(resolved["regions"]) <= 16, view["style"]
        paired = json.dumps({"scene": resolved, "previous": resolved}, separators=(",", ":"))
        assert len(paired) <= scene.MAX_VIEW_BYTES, view["style"]
        for element in resolved["elements"]:
            if element["op"] == "mask":
                assert 0 <= element["x"] - element["width"] // 2, view["style"]
                assert element["x"] + element["width"] // 2 < 240, view["style"]


def test_crisp_never_uses_glyph_masks_and_long_text_is_elided_not_cut(dial):
    scene, canvas = dial.load("scene"), dial.load("canvas")
    for view in views(dial.load("catalogue")):
        resolved = scene.compile_scene({**view, "appearance": {"raster": "crisp"}})
        assert not any(element["op"] == "mask" for element in resolved["elements"]), view["style"]
    for crisp in (True, False):
        c = canvas.Canvas(scene.THEMES["ember"], crisp)
        value, size = c._fit("A very long destination name", 13, 1, 1, 60)
        assert c.text_size(value, size, 1, 1)[0] <= 60
        assert value.endswith("..")


def _contrast(first, second):
    """WCAG contrast ratio of two #RRGGBB colours."""
    light, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _luminance(colour):
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    red, green, blue = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def test_default_text_is_big_and_bright_enough_to_read_on_the_dial(dial, monkeypatch):
    """The owner found the Dial hard to read: 74% of text was 8 px or less, 22% under 4.5:1."""
    scene, catalogue = dial.load("scene"), dial.load("catalogue")
    floor = sys.modules[scene.Canvas.__module__].MIN_TEXT
    drawn = []
    draw = scene.Canvas.text

    def record(self, value, x, y, size, colour, under=None, **options):
        fitted = self._fit(value, size, options.get("tracking", 1), options.get("weight", 0), options.get("max_width"))[1]
        drawn.append((str(value), fitted, round(_contrast(colour, under or self.theme["bg"]), 1)))
        return draw(self, value, x, y, size, colour, under, **options)

    monkeypatch.setattr(scene.Canvas, "text", record)
    for view, raster, theme in product(views(catalogue), ("smooth", "crisp"), scene.THEMES):
        drawn.clear()
        scene.compile_scene({**view, "theme": theme, "appearance": {"raster": raster}})
        poor = [text for text in drawn if text[1] < floor or text[2] < 4.5]
        assert not poor, (view["style"], raster, theme, poor)


@pytest.mark.parametrize("raster", ["smooth", "crisp"])
def test_hiding_the_ring_lets_the_interior_grow_and_still_fit(dial, raster):
    """The owner asked for this: before, only the ring itself went and the space stayed empty."""
    scene, appearance, catalogue = dial.load("scene"), dial.load("appearance"), dial.load("catalogue")
    assert scene._interior_scale("NAV-ORBIT", appearance.DEFAULTS) == 1

    def reach(resolved):
        return max(hypot(region["x"] - 120, region["y"] - 120) for region in resolved["regions"])

    for view in views(catalogue):
        framed = scene.compile_scene({**view, "appearance": {"raster": raster}})
        bare = scene.compile_scene({**view, "appearance": {"raster": raster, "outer-border": False}})
        if view["style"] in appearance.PICTURE_DEFAULTS:
            # A picture can't grow, so nothing around it may move.
            assert all(element in framed["elements"] for element in bare["elements"]), view["style"]
            continue
        assert reach(bare) > reach(framed), view["style"]
        assert len(bare["elements"]) <= 64 and len(bare["regions"]) <= 16, view["style"]
        paired = json.dumps({"scene": bare, "previous": bare}, separators=(",", ":"))
        assert len(paired) <= scene.MAX_VIEW_BYTES, view["style"]


def test_solid_bands_leave_no_unpainted_pixels(dial):
    """The old concentric strokes left about 14% of a thick gauge unpainted."""
    import subprocess
    from math import hypot
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    resolved = {
        "version": 5, "width": 240, "height": 240, "background": "#000000", "label": "", "screen": "", "regions": [],
        "elements": [{"op": "arc", "x": 120, "y": 120, "r": 70, "start": -180, "end": 180, "stroke": "#ffffff", "width": 10, "solid": True}],
    }
    pixels = subprocess.run(["node", "tests/scene_render.mjs"], cwd=root, input=json.dumps([resolved]).encode(), check=True, capture_output=True).stdout
    holes = sum(
        pixels[(y * 240 + x) * 4] == 0
        for y in range(240)
        for x in range(240)
        if 66 <= hypot(x - 120, y - 120) <= 73
    )
    assert holes == 0


ACTIONS = (
    ("light", "LIGHT", ["toggle"]),
    ("cover", "COVER", ["open", "stop", "close"]),
    ("media_player", "MEDIA", ["previous", "play_pause", "next"]),
    ("alarm_control_panel", "SECURITY", ["disarm", "arm_home", "arm_away", "arm_night"]),
)


def test_action_buttons_never_share_a_touch_area_with_back_or_home(dial):
    scene = dial.load("scene")
    for raster, shape, (domain, base, actions) in product(("smooth", "crisp"), SHAPES, ACTIONS):
        resolved = scene.compile_scene({"kind": "control", "id": "c", "domain": domain, "title": "Example", "style": f"CTL-{base}-{shape}", "back": True, "actions": actions, "appearance": {"raster": raster}, **LEVEL})
        chrome = [region for region in resolved["regions"] if region["id"] in {"back", "home"}]
        buttons = [region for region in resolved["regions"] if region["id"] in actions]
        assert len(buttons) == len(actions) and {region["id"] for region in chrome} == {"back", "home"}, (raster, shape, domain)
        for button in buttons:
            for other in chrome:
                assert hypot(button["x"] - other["x"], button["y"] - other["y"]) >= button["r"] + other["r"], (raster, shape, button, other)


def test_a_crowded_page_keeps_back_and_home_within_the_dials_touch_limit(dial):
    """Snake at four a row shows 12 items: three circles each for Back and Home would make 18."""
    scene = dial.load("scene")
    items = [{"id": f"i{n}", "label": f"Item {n}", "icon": "mdi:lightbulb", "children": []} for n in range(30)]
    dense = {"snake-per-row": 4, "snake-row-length": 170, "snake-turn": 14}
    resolved = scene.compile_scene({"kind": "menu", "id": "home", "title": "Home", "style": "NAV-SNAKE", "back": True, "items": items, "selected": 0, "appearance": dense})
    assert len(resolved["regions"]) <= scene.MAX_REGIONS
    assert [region["id"] for region in resolved["regions"]].count("back") == 1
    assert not any("spare" in region for region in resolved["regions"])
    roomy = scene.compile_scene({"kind": "menu", "id": "home", "title": "Home", "style": "NAV-ORBIT", "back": True, "items": items[:6]})
    assert [region["id"] for region in roomy["regions"]].count("back") == 3
    assert not any("spare" in region for region in roomy["regions"])


@pytest.mark.parametrize("chrome_style", ["pill", "circle"])
def test_back_and_home_respond_across_what_is_drawn_and_a_fingertip_beyond(dial, monkeypatch, chrome_style):
    """The owner found them hard to hit: one centred circle left the pills' icons untouchable."""
    scene, catalogue = dial.load("scene"), dial.load("catalogue")
    layout = sys.modules[scene.chrome.__module__]  # The copy scene uses; loading again would make another.
    slack = 5  # About 0.7 mm, at the narrowest point between a pill's touch circles; most of it gets more.
    drawn = []
    shapes = {"pill": scene.Canvas.pill, "disc": scene.Canvas.disc}
    drawing = [False]

    def recorded(kind):
        def draw(self, x, y, *args, **options):
            if drawing[0]:
                drawn.append((kind, x, y, *args[:2]))
            return shapes[kind](self, x, y, *args, **options)
        return draw

    chrome = layout.chrome

    def watched(*args, **options):
        drawing[0] = True
        try:
            return chrome(*args, **options)
        finally:
            drawing[0] = False

    monkeypatch.setattr(scene.Canvas, "pill", recorded("pill"))
    monkeypatch.setattr(scene.Canvas, "disc", recorded("disc"))
    monkeypatch.setattr(layout, "chrome", watched)
    monkeypatch.setattr(scene, "chrome", watched)
    controls = [
        {"kind": "control", "id": "c", "domain": domain, "title": "Example", "style": f"CTL-{base}-{shape}", "back": True, "actions": actions, **LEVEL}
        for shape, (domain, base, actions) in product(SHAPES, ACTIONS)
    ]
    for view in [*views(catalogue), *controls]:
        drawn.clear()
        resolved = scene.compile_scene({**view, "appearance": {"chrome-style": chrome_style}})
        regions = [region for region in resolved["regions"] if region["id"] in {"back", "home"}]
        assert len(drawn) == 2, (view["style"], drawn)
        for kind, x, y, first, second in drawn:
            # A pill is a capsule: every point within radius of its centre line. A disc has no length.
            half, radius = (first / 2 - second / 2, second / 2) if kind == "pill" else (0, first)
            outline = [
                (px, py)
                for px in range(round(x - half - radius - slack), round(x + half + radius + slack) + 1)
                for py in range(round(y - radius - slack), round(y + radius + slack) + 1)
                if hypot(px - min(max(px, x - half), x + half), py - y) <= radius + slack
            ]
            missed = [point for point in outline if not any(hypot(point[0] - region["x"], point[1] - region["y"]) <= region["r"] for region in regions)]
            assert not missed, (view["style"], kind, len(missed), missed[:3], regions)


def test_the_confirm_question_replaces_the_state_line(dial):
    layout = dial.load("control_layout")
    assert layout.detail_text({"state": "closed", "confirmation": "open"}) == ""
    assert layout.detail_text({"state": "closed"}) == "CLOSED"


def door(dial, raster="smooth", **values):
    scene = dial.load("scene")
    return scene.compile_scene({"kind": "control", "id": "c", "domain": "cover", "title": "Garage door", "style": "CTL-COVER-INSTRUMENT", "back": True, "confirm": True, "available": True, "actions": ["open", "stop", "close"], "appearance": {"raster": raster}, "value": 0, "state": "closed", **values})


def spoken(dial, **values):
    """The door's main line, captured as it's drawn."""
    canvas = dial.load("canvas")
    door(dial)  # Loads the modules the capture below replaces a method on.
    said = []
    original = canvas.Canvas.text

    def capture(self, value, *args, **kwargs):
        said.append(value)
        return original(self, value, *args, **kwargs)

    scene = sys.modules["dial_test.scene"]
    scene.Canvas.text = capture
    try:
        door(dial, **values)
    finally:
        scene.Canvas.text = original
    return said


@pytest.mark.parametrize(
    "values,expected",
    [
        ({}, "CLOSED"),
        ({"state": "open", "value": 100}, "OPEN"),
        ({"state": "opening", "value": 40}, "OPENING 40%"),
        ({"state": "opening", "value": 100, "position_known": False}, "OPENING"),
        ({"confirmation": "open", "device_class": "garage"}, "OPEN THE DOOR?"),
        ({"confirmation": "close", "device_class": "gate"}, "CLOSE THE GATE?"),
        ({"confirmation": "open"}, "OPEN?"),
        ({"pending": True}, "PENDING"),
    ],
)
def test_a_door_says_what_it_is_doing_in_words(dial, values, expected):
    said = spoken(dial, **values)
    assert expected in said, said
    assert not any(text.startswith("CONFIRM") for text in said), "the door asks in its own line"


def test_a_cover_you_can_turn_keeps_its_live_number_and_a_door_has_none(dial):
    scene = dial.load("scene")
    blind = scene.compile_scene({"kind": "control", "id": "c", "domain": "cover", "title": "Blind", "style": "CTL-COVER-INSTRUMENT", "continuous": True, "available": True, "actions": ["open", "stop", "close"], "value": 40, "state": "open", "unit": "%"})
    assert any(element["op"] == "number" for element in blind["elements"])
    assert any(element["op"] == "gauge" for element in blind["elements"])
    shut = door(dial)
    assert not any(element["op"] in {"number", "gauge"} for element in shut["elements"])


CONFIRMED = (
    ("lock", "CTL-LOCK-INSTRUMENT", {"state": "locked", "actions": ["unlock"], "confirmation": "unlock"}, "UNLOCK?", "LOCKED"),
    ("alarm_control_panel", "CTL-SECURITY-INSTRUMENT", {"state": "armed_away", "actions": ["disarm"], "confirmation": "disarm"}, "DISARM?", "ARMED AWAY"),
    ("scene", "CTL-SCENE-INSTRUMENT", {"actions": ["activate"], "confirmation": "activate"}, "CONFIRM ACTIVATE?", "ACTIVATE"),
    ("switch", "CTL-SWITCH-INSTRUMENT", {"active": True, "state": "on", "confirmation": "toggle"}, "CONFIRM TOGGLE?", "ON"),
    ("vacuum", "CTL-VACUUM-INSTRUMENT", {"state": "docked", "actions": ["start"], "confirmation": "start"}, "CONFIRM START?", "DOCKED"),
)


@pytest.mark.parametrize("domain,style,values,question,state", CONFIRMED)
def test_asking_replaces_the_state_word_wherever_it_would_land(dial, domain, style, values, question, state):
    scene = dial.load("scene")
    said = []
    original = scene.Canvas.text

    def capture(self, value, *args, **kwargs):
        said.append(value)
        return original(self, value, *args, **kwargs)

    scene.Canvas.text = capture
    try:
        scene.compile_scene({"kind": "control", "id": "c", "domain": domain, "title": "Example", "style": style, "back": True, "confirm": True, "available": True, "value": 0, **values})
    finally:
        scene.Canvas.text = original
    assert question in said, said
    assert state not in said, said
