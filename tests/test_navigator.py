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
    ).Navigator()

    assert navigator.current()["id"] == "root"
    assert navigator.input("press")["id"] == "lights"
    control = navigator.input("touch", "kitchen")
    assert control["kind"] == "control"
    assert control["entity_id"] == "light.example_kitchen"
    assert control["value"] == 50
    assert navigator.input("rotate_right")["value"] == 55
    assert navigator.input("rotate_left")["value"] == 50
    assert navigator.input("press")["active"] is False
    assert navigator.input("back")["id"] == "lights"
    assert navigator.input("back")["id"] == "root"


def test_rotation_wraps():
    navigator = load(
        "ha_dial_navigator_rotation", "custom_components/ha_dial/navigator.py"
    ).Navigator()

    assert navigator.input("rotate_left")["selected"] == 2
    assert navigator.input("rotate_right")["selected"] == 0
