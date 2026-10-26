import importlib.util
from pathlib import Path


def load(name: str, relative: str):
    path = Path(__file__).parents[1] / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_navigation_materialises_only_the_current_screen():
    navigator = load(
        "ha_dial_navigator", "custom_components/ha_dial/navigator.py"
    ).Navigator("light.example", "Demo light")

    assert navigator.current()["id"] == "root"
    assert navigator.input("press")["id"] == "lights"
    control = navigator.input("touch", "light.example")
    assert control["kind"] == "control"
    assert control["entity_id"] == "light.example"
    assert control["value"] == 50
    assert navigator.input("rotate_right")["value"] == 55
    assert navigator.input("rotate_right")["value"] == 60
    assert navigator.input("rotate_left")["value"] == 55
    assert navigator.input("press")["active"] is False
    assert navigator.input("back")["id"] == "lights"
    assert navigator.input("back")["id"] == "root"


def test_rotation_wraps():
    navigator = load(
        "ha_dial_navigator_rotation", "custom_components/ha_dial/navigator.py"
    ).Navigator("light.example", "Demo light")

    assert navigator.input("rotate_left")["selected"] == 0
    assert navigator.input("rotate_right")["selected"] == 0


def test_unavailable_control_ignores_input_and_accepts_state_sync():
    navigator = load(
        "ha_dial_navigator_sync", "custom_components/ha_dial/navigator.py"
    ).Navigator("light.example", "Demo light")

    navigator.input("press")
    navigator.input("press")
    navigator.sync(0, False, False)
    assert navigator.input("rotate_right")["value"] == 0
    assert navigator.input("press")["active"] is False

    navigator.sync(72, True, True, "Renamed light")
    assert navigator.current()["value"] == 72
    assert navigator.current()["active"] is True
    assert navigator.current()["title"] == "Renamed light"


def test_absolute_value_is_clamped():
    navigator = load(
        "ha_dial_navigator_absolute", "custom_components/ha_dial/navigator.py"
    ).Navigator("light.example", "Demo light")

    navigator.input("press")
    navigator.input("press")
    assert navigator.input("set_value", value=73)["value"] == 73
    assert navigator.input("set_value", value=101)["value"] == 100
