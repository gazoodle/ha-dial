"""Contracts for Atlas options, domain adapters, visibility and settings overflow."""

import json
from types import SimpleNamespace

import pytest
from jinja2.nativetypes import NativeEnvironment


def test_domain_styles_compile_and_remain_bounded(integration, dial):
    catalogue = dial.load("catalogue")
    definition = dial.load("definition")
    nav_type = dial.load("navigator").Navigator
    controls = dial.load("controls")
    protocol = dial.load("protocol")
    for domain in catalogue.CONTROL_TYPES:
        state = SimpleNamespace(
            state="on",
            attributes={
                "friendly_name": "Example",
                "supported_features": 65535,
                "temperature": 21.5,
                "current_temperature": 20,
                "hvac_modes": ["heat", "off"],
                "percentage": 40,
                "volume_level": 0.4,
                "options": ["on", "off"],
            },
        )
        for style in catalogue.control_styles(domain):
            tree = definition.build_definition(
                SimpleNamespace(states={domain + ".demo": state}),
                [
                    {
                        "id": "root",
                        "title": "Home",
                        "entities": [
                            {
                                "entity_id": domain + ".demo",
                                "style": style,
                                "icon": "mdi:star",
                                "appearance": {"raster": "crisp"},
                            }
                        ],
                    }
                ],
                "ember",
            )
            nav = nav_type(definition=tree)
            view = nav.input("press")
            nav.sync(**controls.control_state(domain + ".demo", state))
            view = nav.current()
            encoded = protocol.device_payload(view, nav.previous(), 1)
            payload = json.loads(encoded)
            assert len(encoded.encode()) <= 24576
            assert len(payload["scene"]["elements"]) <= 64
            assert len(payload["scene"]["regions"]) <= 16
            assert "entity_id" not in payload
            if domain in {"sensor", "binary_sensor", "weather", "calendar"}:
                assert controls.control_command(view, "press", None) is None


def test_raster_border_css_and_icons(dial):
    scene = dial.load("scene")
    assets = dial.load("assets")
    view = {
        "id": "root",
        "kind": "menu",
        "title": "Home",
        "items": [{"id": "demo", "label": "Example", "icon": "mdi:star"}],
    }
    original = scene.compile_scene(view)
    styled = scene.compile_scene(
        {
            **view,
            "css": "outer-border: off; accent: #00ff00; raster: crisp; icon-size: 24px;",
        }
    )
    assert not any(e.get("r") == 116 for e in styled["elements"])
    assert original != styled
    highlighted = scene.compile_scene({**view, "appearance": {"highlight-radius": 24}})
    assert any(e.get("r") == 24 for e in highlighted["elements"])
    hub = scene.compile_scene({**view, "appearance": {"hub-radius": 42}})
    assert any(e.get("r") == 42 for e in hub["elements"])
    control = scene.compile_scene(
        {
            "kind": "control",
            "id": "demo",
            "domain": "light",
            "title": "Light",
            "style": "CTL-LIGHT-INSTRUMENT",
            "value": 50,
            "appearance": {"gauge-radius": 80, "gauge-width": 4},
        }
    )
    assert any(
        e.get("op") == "gauge" and e["r"] == 80 and e["width"] == 4
        for e in control["elements"]
    )
    petals = scene.compile_scene({**view, "style": "NAV-PETALS"})
    assert not any(e.get("r") == 18 for e in petals["elements"])
    assert petals["version"] == 5
    paths = [e for e in petals["elements"] if e["op"] == "polyline"]
    assert len(paths) == 1
    assert paths[0]["points"][0] == paths[0]["points"][-1]
    hub_index = next(i for i, e in enumerate(petals["elements"]) if e.get("r") == 32)
    assert all(e["op"] != "polyline" for e in petals["elements"][hub_index:])
    # Crisp is line-step strokes: thresholded glyph masks are what the owner ruled out.
    crisp = scene.compile_scene({**view, "appearance": {"raster": "crisp"}})
    assert not any(e["op"] == "mask" for e in crisp["elements"])
    assert any(e["op"] == "segments" for e in crisp["elements"])
    smooth = scene.compile_scene({**view, "appearance": {"raster": "smooth"}})
    assert any(e["op"] == "mask" for e in smooth["elements"])
    assert all("background" in e for e in smooth["elements"] if e["op"] not in {"number"})
    for css in [
        "position: fixed;",
        "accent: red;",
        "orbit-radius: 1000;",
        "highlight-radius: 33;",
        "gauge-width: 17;",
        "outer-border: maybe;",
    ]:
        with pytest.raises(ValueError):
            scene.compile_scene({**view, "css": css})


def test_conditions_track_hidden_branches_and_restore_nearest_ancestor(
    integration, dial
):
    i = integration
    env = NativeEnvironment()
    env.globals["states"] = lambda entity: (
        i.hass.states.get(entity).state if i.hass.states.get(entity) else "unknown"
    )
    env.globals["state_attr"] = lambda entity, attr: (
        i.hass.states.get(entity).attributes.get(attr)
        if i.hass.states.get(entity)
        else None
    )
    env.filters["is_number"] = lambda value: str(value).replace(".", "", 1).isdigit()

    class Template:
        def __init__(self, source, hass):
            self.source = source

        def async_render(self, variables=None, parse_result=True):
            return env.from_string(self.source).render(**(variables or {}))

    dial.module("homeassistant.helpers.template", Template=Template)
    definition = dial.load("definition")
    visibility = dial.load("visibility")
    nav_type = dial.load("navigator").Navigator
    i.hass.states["switch.demo"] = SimpleNamespace(state="on", attributes={})
    pages = [
        {"id": "root", "title": "Home"},
        {"id": "floor", "title": "Floor", "parent": "root"},
        {
            "id": "room",
            "title": "Room",
            "parent": "floor",
            "conditions": [
                {"condition": "state", "entity_id": "switch.demo", "state": "on"}
            ],
            "entities": [
                {
                    "entity_id": "light.demo",
                    "conditions": [
                        {
                            "condition": "numeric_state",
                            "entity_id": "sensor.demo",
                            "above": 10,
                        }
                    ],
                }
            ],
        },
    ]
    raw = definition.build_definition(i.hass, pages, "ember")
    filtered = visibility.filter_definition(i.hass, raw)
    nav = nav_type(definition=filtered)
    nav.input("press")
    nav.input("press")
    assert nav.current()["title"] == "Room"
    assert not nav.current()["items"]
    i.hass.states["switch.demo"].state = "off"
    hidden = visibility.filter_definition(i.hass, raw)
    restored = nav_type(definition=hidden)
    restored.restore(nav)
    assert restored.current()["title"] == "Floor"
    assert hidden["_condition_entities"] == ["sensor.demo", "switch.demo"]
    assert hidden["_condition_templates"] == []
    assert len(raw["tree"]["items"][0]["children"]) == 1
    with pytest.raises(ValueError, match="fixed time"):
        definition.build_definition(
            i.hass,
            [
                {
                    "id": "root",
                    "title": "Home",
                    "conditions": [{"condition": "time", "after": "invalid"}],
                }
            ],
            "ember",
        )


def test_settings_is_ninth_rotary_item_not_ninth_orbit(dial):
    nav_type = dial.load("navigator").Navigator
    scene = dial.load("scene")
    root = {
        "id": "root",
        "title": "Home",
        "items": [
            {"id": f"p{n}", "label": f"Page {n}", "children": []} for n in range(8)
        ],
    }
    nav = nav_type(definition={"tree": root})
    assert len(nav.current()["items"]) == 8
    nav.settings_enabled = True
    for _ in range(8):
        nav.input("rotate_right")
    view = nav.current()
    assert view["selected"] == 8 and len(view["items"]) == 9
    compiled = scene.compile_scene(view)
    cog = next(r for r in compiled["regions"] if r["id"] == "__settings")
    assert (cog["x"], cog["y"]) == (120, 70)
    assert len(compiled["elements"]) <= 64
    assert nav.input("press")["kind"] == "settings"
    assert nav.input("press")["kind"] == "menu"
    nav.settings_enabled = False
    assert all(not item.get("settings") for item in nav.current()["items"])


def test_lock_needs_confirmation_and_pin_required_lock_has_no_action(integration, dial):
    definition = dial.load("definition")
    nav_type = dial.load("navigator").Navigator
    controls = dial.load("controls")
    state = SimpleNamespace(state="locked", attributes={"friendly_name": "Example"})
    tree = definition.build_definition(
        SimpleNamespace(states={"lock.demo": state}),
        [{"id": "root", "title": "Home", "entities": ["lock.demo"]}],
        "ember",
    )
    nav = nav_type(definition=tree)
    nav.input("press")
    nav.sync(**controls.control_state("lock.demo", state))
    first = nav.input("press")
    assert first["confirmation"] == "unlock"
    assert controls.control_command(first, "press", None) is None
    confirmed = nav.input("press")
    assert controls.control_command(confirmed, "press", None) == (
        "lock",
        "unlock",
        {"entity_id": "lock.demo"},
    )
    assert controls.control_command(confirmed, "ready", None) is None
    ready = nav.input("ready")
    assert "_confirmed" not in ready
    assert controls.control_command(ready, "ready", None) is None
    state.attributes["code_format"] = "number"
    assert controls.control_state("lock.demo", state)["actions"] == []


def test_every_navigation_layout_keeps_all_items_reachable_and_fits(dial):
    nav_type = dial.load("navigator").Navigator
    scene = dial.load("scene")
    catalogue = dial.load("catalogue")
    for style in catalogue.NAV_STYLES:
        for count in range(9):
            root = {
                "id": "root",
                "title": "Example",
                "style": style,
                "items": [
                    {
                        "id": f"p{n}",
                        "label": f"Page {n}",
                        "icon": "mdi:folder",
                        "children": [],
                    }
                    for n in range(count)
                ],
            }
            nav = nav_type(definition={"tree": root})
            nav.settings_enabled = True
            for selected in range(count + 1):
                compiled = scene.compile_scene(nav.current())
                assert len(compiled["elements"]) <= 64, (style, count)
                assert len(compiled["regions"]) <= 16
                assert any(r["id"] == "__settings" for r in compiled["regions"])
                if selected < count:
                    assert any(
                        r["id"] == f"p{selected}" for r in compiled["regions"]
                    ), (style, count, selected)
                nav.input("rotate_right")


def test_editor_catalogue_matches_backend(dial):
    from pathlib import Path

    catalogue = dial.load("catalogue")
    text = (
        Path(__file__).resolve().parents[1]
        / "custom_components/ha_dial/www/editor/catalogue.js"
    ).read_text()
    for name, expected in [
        ("DOMAINS", list(catalogue.CONTROL_TYPES)),
        ("NAV_STYLES", sorted(catalogue.PAGE_STYLES)),
        (
            "CONTROL_STYLES",
            {d: sorted(catalogue.control_styles(d)) for d in catalogue.CONTROL_TYPES},
        ),
    ]:
        line = next(
            line
            for line in text.splitlines()
            if line.startswith(f"export const {name} = ")
        )
        assert json.loads(line.split(" = ", 1)[1].removesuffix(";")) == expected


def test_single_option_and_fixed_number_do_not_offer_rotary(integration, dial):
    controls = dial.load("controls")
    for domain, attrs in [
        ("select", {"options": ["Only"]}),
        ("number", {"min": 10, "max": 10, "step": 1}),
        ("climate", {"temperature": 21, "supported_features": 0}),
    ]:
        state = SimpleNamespace(
            state="Only" if domain == "select" else "10", attributes=attrs
        )
        assert not controls.control_state(domain + ".demo", state)["continuous"]
    controls.control_state(
        "media_player.demo",
        SimpleNamespace(state="off", attributes={"volume_level": None}),
    )


@pytest.mark.parametrize(
    ("domain", "value", "field", "service", "expected"),
    [
        ("climate", 21.5, "temperature", "set_temperature", 21.5),
        ("media_player", 42, "volume_level", "volume_set", 0.42),
        ("fan", 42, "percentage", "set_percentage", 42),
        ("number", 42, "value", "set_value", 42),
        ("input_number", 42, "value", "set_value", 42),
        ("select", 1, "option", "select_option", "Boost"),
        ("input_select", 1, "option", "select_option", "Boost"),
    ],
)
def test_domain_rotary_commands(
    integration, dial, domain, value, field, service, expected
):
    controls = dial.load("controls")
    view = {
        "entity_id": domain + ".demo",
        "domain": domain,
        "available": True,
        "continuous": True,
        "value": value,
        "options": ["Quiet", "Boost"],
    }
    assert controls.control_command(view, "set_value", None) == (
        domain,
        service,
        {"entity_id": domain + ".demo", field: expected},
    )


@pytest.mark.parametrize(
    ("domain", "expected"),
    [("light", "turn_off"), ("switch", "turn_off"), ("cover", "stop_cover")],
)
def test_confirmed_power_and_cover_press_execute_the_named_action(
    integration, dial, domain, expected
):
    definition = dial.load("definition")
    nav_type = dial.load("navigator").Navigator
    controls = dial.load("controls")
    tree = definition.build_definition(
        SimpleNamespace(states={}),
        [
            {
                "id": "root",
                "title": "Home",
                "entities": [{"entity_id": domain + ".demo", "confirm": True}],
            }
        ],
        "ember",
    )
    nav = nav_type(definition=tree)
    nav.input("press")
    state = SimpleNamespace(
        state="open" if domain == "cover" else "on",
        attributes={"supported_features": 15, "current_position": 50},
    )
    nav.sync(**controls.control_state(domain + ".demo", state))
    if domain == "cover":
        # Stop is exempt from confirmation: stopping a moving door must never wait on a prompt.
        assert controls.control_command(nav.input("press"), "press", None) == (
            domain,
            expected,
            {"entity_id": domain + ".demo"},
        )
        return
    assert controls.control_command(nav.input("press"), "press", None) is None
    assert controls.control_command(nav.input("press"), "press", None) == (
        domain,
        expected,
        {"entity_id": domain + ".demo"},
    )


def _confirmed_cover(dial):
    definition, controls = dial.load("definition"), dial.load("controls")
    tree = definition.build_definition(
        SimpleNamespace(states={}),
        [{"id": "root", "title": "Home", "entities": [{"entity_id": "cover.door", "confirm": True}]}],
        "ember",
    )
    nav = dial.load("navigator").Navigator(definition=tree)
    nav.input("press")
    state = SimpleNamespace(state="closed", attributes={"supported_features": 15, "current_position": 0})
    nav.sync(**controls.control_state("cover.door", state))
    return nav, controls


@pytest.mark.parametrize("action,value", [("rotate_right", None), ("rotate_left", None), ("set_value", 80)])
def test_turning_the_dial_never_moves_a_cover_that_needs_confirming(integration, dial, action, value):
    nav, controls = _confirmed_cover(dial)
    before = nav.current()["value"]
    view = nav.input(action, None, value)
    assert view["value"] == before and not view["pending"]
    assert controls.control_command(view, action, None) is None


def test_opening_a_cover_that_needs_confirming_still_asks(integration, dial):
    nav, controls = _confirmed_cover(dial)
    view = nav.input("touch", "open")
    assert view["confirmation"] == "open"
    assert controls.control_command(view, "touch", "open") is None
    confirmed = nav.input("press")
    assert controls.control_command(confirmed, "press", None) == ("cover", "open_cover", {"entity_id": "cover.door"})


def test_a_cover_that_needs_no_confirming_still_turns(integration, dial):
    definition, controls = dial.load("definition"), dial.load("controls")
    tree = definition.build_definition(SimpleNamespace(states={}), [{"id": "root", "title": "Home", "entities": ["cover.blind"]}], "ember")
    nav = dial.load("navigator").Navigator(definition=tree)
    nav.input("press")
    state = SimpleNamespace(state="open", attributes={"supported_features": 15, "current_position": 50})
    nav.sync(**controls.control_state("cover.blind", state))
    view = nav.input("rotate_right")
    assert controls.control_command(view, "rotate_right", None)[1] == "set_cover_position"


def test_an_icon_the_dial_cannot_draw_falls_back_instead_of_rejecting_the_tree(dial):
    definition = dial.load("definition")
    state = SimpleNamespace(attributes={"icon": "hue:bulb-group", "friendly_name": "Lamp"})
    tree = definition.build_definition(SimpleNamespace(states={"light.lamp": state}), [{"id": "root", "title": "Home", "entities": ["light.lamp"]}], "ember")
    assert tree["tree"]["items"][0]["icon"] == "mdi:lightbulb"


def test_a_rebuilt_tree_keeps_the_selected_item_and_survives_open_settings(dial):
    navigator = dial.load("navigator").Navigator

    def tree(*ids):
        return {"tree": {"id": "root", "title": "Home", "items": [{"id": name, "label": name, "icon": "mdi:folder", "children": []} for name in ids]}}

    old = navigator(definition=tree("a", "b", "c"))
    old.selected = 2
    fresh = navigator(definition=tree("new", "a", "b", "c"))
    fresh.restore(old)
    assert fresh.current()["items"][fresh.selected]["id"] == "c"

    old.settings_enabled = True
    old.selected = 3
    old.input("press")
    assert old.control["kind"] == "settings"
    navigator(definition=tree("a")).restore(old)


def test_numeric_visibility_accepts_signed_literal_bounds_and_rejects_ignored_options(
    dial,
):
    visibility = dial.load("visibility")
    expression = visibility.condition_template(
        {"condition": "numeric_state", "entity_id": "sensor.example", "below": "-1.5"}
    )
    assert 'states("-1.5")' not in expression
    env = NativeEnvironment()
    env.globals["states"] = lambda entity: "-5"
    env.filters["is_number"] = lambda value: True
    assert env.from_string(expression).render() is True
    with pytest.raises(ValueError, match="template condition"):
        visibility.condition_template(
            {
                "condition": "numeric_state",
                "entity_id": "sensor.example",
                "above": 0,
                "value_template": "{{ 5 }}",
            }
        )
