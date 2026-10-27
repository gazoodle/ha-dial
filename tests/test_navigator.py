def test_navigation_materialises_only_the_current_screen(dial):
    navigator = dial.load("navigator").Navigator("light.example", "Demo light")

    assert navigator.current()["id"] == "root"
    lights_id = navigator.input("press")["id"]
    assert lights_id != "root"
    control = navigator.input("touch", "light.example")
    assert control["kind"] == "control"
    assert control["entity_id"] == "light.example"
    assert control["value"] == 50
    assert navigator.input("rotate_right")["value"] == 55
    assert navigator.input("rotate_right")["value"] == 60
    assert navigator.input("rotate_left")["value"] == 55
    assert navigator.input("press")["active"] is False
    assert navigator.input("back")["id"] == lights_id
    assert navigator.input("back")["id"] == "root"


def test_rotation_wraps(dial):
    navigator = dial.load("navigator").Navigator("light.example", "Demo light")

    assert navigator.input("rotate_left")["selected"] == 0
    assert navigator.input("rotate_right")["selected"] == 0


def test_unavailable_control_ignores_input_and_accepts_state_sync(dial):
    navigator = dial.load("navigator").Navigator("light.example", "Demo light")

    navigator.input("press")
    navigator.input("press")
    navigator.sync(0, False, False)
    assert navigator.input("rotate_right")["value"] == 0
    assert navigator.input("press")["active"] is False

    navigator.sync(72, True, True, "Renamed light")
    assert navigator.current()["value"] == 72
    assert navigator.current()["active"] is True
    assert navigator.current()["title"] == "Renamed light"


def test_absolute_value_is_clamped(dial):
    navigator = dial.load("navigator").Navigator("light.example", "Demo light")

    navigator.input("press")
    navigator.input("press")
    assert navigator.input("set_value", value=73)["value"] == 73
    assert navigator.input("set_value", value=101)["value"] == 100
