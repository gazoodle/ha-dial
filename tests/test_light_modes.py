"""White and colour on lights: what each mode turns, what it sends, and that it fits the Dial."""

import json
from itertools import product
from types import SimpleNamespace

import pytest

COLOUR_LIGHT = {"supported_color_modes": ["color_temp", "hs"], "brightness": 128, "color_temp_kelvin": 3000, "min_color_temp_kelvin": 2200, "max_color_temp_kelvin": 6000, "hs_color": [200, 80], "friendly_name": "Lamp"}
SHAPES = ("INSTRUMENT", "EDITORIAL", "COLUMN", "SEGMENT", "TUMBLER")


def opened(integration, dial, attributes, state="on"):
    definition, navigator = dial.load("definition"), dial.load("navigator")
    controls = dial.load("controls")
    tree = definition.build_definition(SimpleNamespace(states={}), [{"id": "root", "title": "Home", "entities": ["light.lamp"]}], "ember")
    nav = navigator.Navigator(definition=tree)
    nav.input("press")
    light = SimpleNamespace(state=state, attributes=attributes)
    resync = lambda: nav.sync(**controls.control_state("light.lamp", light))
    resync()
    return nav, controls, resync


def test_turning_starts_on_brightness_and_the_button_moves_through_what_the_light_can_do(integration, dial):
    nav, _, _ = opened(integration, dial, COLOUR_LIGHT)
    view = nav.current()
    assert (view["value"], view["unit"], view["actions"]) == (50, "%", ["light_mode"])
    view = nav.input("touch", "light_mode")
    assert (view["light_mode"], view["value"], view["minimum"], view["maximum"], view["unit"], view["detail"]) == ("white", 3000, 2200, 6000, "K", "WHITE")
    view = nav.input("touch", "light_mode")
    assert (view["light_mode"], view["value"], view["minimum"], view["maximum"], view["unit"], view["detail"]) == ("colour", 200, 0, 359, "°", "COLOUR")
    view = nav.input("touch", "light_mode")
    assert (view["light_mode"], view["value"], view["unit"]) == ("brightness", 50, "%")
    assert "detail" not in view


@pytest.mark.parametrize(
    "modes,expected",
    [(["color_temp"], ["white", "brightness"]), (["hs"], ["colour", "brightness"]), (["rgbww"], ["colour", "brightness"]), (["xy", "color_temp"], ["white", "colour", "brightness"])],
)
def test_only_what_a_light_can_do_is_offered(integration, dial, modes, expected):
    nav, _, _ = opened(integration, dial, {"supported_color_modes": modes, "brightness": 128})
    assert [nav.input("touch", "light_mode")["light_mode"] for _ in expected] == expected


@pytest.mark.parametrize("modes", [["brightness"], ["onoff"], []])
def test_a_plain_light_gets_no_button(integration, dial, modes):
    nav, _, _ = opened(integration, dial, {"supported_color_modes": modes, "brightness": 128})
    assert nav.current()["actions"] == []


@pytest.mark.parametrize(
    "presses,data",
    [
        (0, {"brightness_pct": 55}),
        (1, {"color_temp_kelvin": 3100}),
        (2, {"hs_color": [210, 80]}),
    ],
)
def test_each_mode_sends_what_it_turns(integration, dial, presses, data):
    nav, controls, _ = opened(integration, dial, COLOUR_LIGHT)
    for _ in range(presses):
        nav.input("touch", "light_mode")
    view = nav.input("rotate_right")
    assert controls.control_command(view, "rotate_right", None) == ("light", "turn_on", {"entity_id": "light.lamp", **data})


def test_the_dials_own_turn_arrives_as_a_value_in_the_same_range(integration, dial):
    nav, controls, _ = opened(integration, dial, COLOUR_LIGHT)
    nav.input("touch", "light_mode")
    view = nav.input("set_value", None, 4500)
    assert controls.control_command(view, "set_value", None)[2]["color_temp_kelvin"] == 4500
    assert nav.input("set_value", None, 99999)["value"] == 6000, "held to what the light can do"


def test_changing_mode_sends_nothing_and_never_asks(integration, dial):
    nav, controls, _ = opened(integration, dial, COLOUR_LIGHT)
    nav.control["confirm"] = True
    view = nav.input("touch", "light_mode")
    assert "confirmation" not in view and not view["pending"]
    assert controls.control_command(view, "touch", "light_mode") is None


def test_press_still_toggles_in_every_mode(integration, dial):
    nav, controls, _ = opened(integration, dial, COLOUR_LIGHT)
    nav.input("touch", "light_mode")
    view = nav.input("press")
    assert controls.control_command(view, "press", None)[1] == "turn_off"


def test_a_lights_rounding_doesnt_leave_it_pending_forever(integration, dial):
    nav, _, _ = opened(integration, dial, {**COLOUR_LIGHT})
    nav.input("touch", "light_mode")
    assert nav.input("rotate_right")["pending"]
    nav.control["target_value"] = 3100
    attributes = {**COLOUR_LIGHT, "color_temp_kelvin": 3115}  # Lights work in mireds, so what comes back is close.
    nav.sync(**dial.load("controls").control_state("light.lamp", SimpleNamespace(state="on", attributes=attributes)))
    assert not nav.current()["pending"]
    assert nav.current()["value"] == 3115


def test_a_report_of_brightness_doesnt_overwrite_another_modes_value(integration, dial):
    nav, _, resync = opened(integration, dial, COLOUR_LIGHT)
    nav.input("touch", "light_mode")
    resync()
    view = nav.current()
    assert (view["light_mode"], view["value"], view["brightness"]) == ("white", 3000, 50)


def test_a_light_that_is_off_starts_somewhere_it_can_show(integration, dial):
    nav, _, _ = opened(integration, dial, {"supported_color_modes": ["color_temp", "hs"]}, state="off")
    assert nav.input("touch", "light_mode")["value"] == 4200, "the middle of its range"
    assert nav.input("touch", "light_mode")["value"] == 0


def test_what_you_turned_to_is_still_there_when_you_come_back_in_a_preview(integration, dial):
    nav, _, _ = opened(integration, dial, COLOUR_LIGHT)
    nav.input("touch", "light_mode")
    nav.input("rotate_right")
    nav.input("touch", "light_mode")
    nav.input("touch", "light_mode")
    assert nav.input("touch", "light_mode")["value"] == 3100


def test_preview_changes_nothing_real_and_a_live_preview_does(integration):
    i = integration
    i.hass.states["light.example"] = SimpleNamespace(state="on", attributes=COLOUR_LIGHT)
    source = {"pages": [{"id": "home", "title": "Home", "entities": ["light.example"]}]}

    async def run():
        await i.code._ws_configure(i.hass, i.connection, {"id": 1, "device": "preview_colour", "definition": source})
        await i.code._input(i.hass, "preview_colour", "press")
        await i.code._input(i.hass, "preview_colour", "touch", "light_mode")
        i.hass.services.async_call.reset_mock()
        view = await i.code._input(i.hass, "preview_colour", "rotate_right")
        i.hass.services.async_call.assert_not_called()
        assert view["value"] == 3100 and not view["pending"]
        await i.code._input(i.hass, "preview_colour", "rotate_right", live=True)
        assert i.hass.services.async_call.call_args.args[:2] == ("light", "turn_on")
        assert i.hass.services.async_call.call_args.args[2]["color_temp_kelvin"] == 3200

    import asyncio

    asyncio.run(run())


def test_it_fits_what_firmware_accepts(dial):
    scene = dial.load("scene")
    modes = {"white": {"value": 6500, "minimum": 2000, "maximum": 6500, "step": 100, "unit": "K", "detail": "WHITE"}, "colour": {"value": 359, "minimum": 0, "maximum": 359, "step": 10, "unit": "°", "detail": "COLOUR"}}
    for (mode, values), shape, raster in product(modes.items(), SHAPES, ("smooth", "crisp")):
        resolved = scene.compile_scene({"kind": "control", "id": "c", "domain": "light", "title": "Lamp", "style": f"CTL-LIGHT-{shape}", "icon": "mdi:lightbulb", "available": True, "active": True, "continuous": True, "state": "on", "actions": ["light_mode"], "back": True, "light_mode": mode, "appearance": {"raster": raster}, **values})
        assert resolved["version"] == 5, "no firmware change is needed"
        assert len(resolved["elements"]) <= 64, (mode, shape, raster)
        assert len(json.dumps({"scene": resolved, "previous": resolved}, separators=(",", ":"))) <= scene.MAX_VIEW_BYTES, (mode, shape, raster)
        colours = {element.get("stroke") for element in resolved["elements"]} | {element.get("fill") for element in resolved["elements"]}
        assert len(colours) > 3, (mode, shape, raster)


def test_the_mode_button_has_a_real_drawing_in_crisp(dial):
    layout, strokes = dial.load("control_layout"), dial.load("strokes")
    icon = layout.ACTION_ICONS["light_mode"]
    assert icon not in {f"mdi:{name}" for name in strokes.ATLAS_ICONS}, "the Atlas maps some names to unrelated drawings"
    assert strokes.icon_paths(icon)


def test_white_runs_warm_to_cool_and_colours_are_real(dial):
    modes = dial.load("light_modes")
    def channels(colour):
        return tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))
    warm, cool = channels(modes.kelvin_colour(2000)), channels(modes.kelvin_colour(6500))
    assert warm[0] == 255 and warm[2] < 60, "warm is orange"
    assert cool[0] == 255 and cool[1] > 240 and cool[2] > 240, "cool is near white"
    assert modes.hue_colour(0) == "#ff0000" and modes.hue_colour(120) == "#00ff00" and modes.hue_colour(240) == "#0000ff"
