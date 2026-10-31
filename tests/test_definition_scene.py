import json
from types import SimpleNamespace

import pytest


def test_pages_empty_layers_and_validation(dial):
    definition = dial.load("definition")
    hass = SimpleNamespace(states={})
    pages = [
        {"id": "root", "title": "Home"},
        {"id": "empty", "title": "Empty", "parent": "root"},
    ]
    result = definition.build_definition(hass, pages, "cobalt")
    assert list(definition.leaf_items(result["tree"])) == []
    assert result["tree"]["items"][0]["theme"] == "cobalt"
    with pytest.raises(ValueError, match="connect"):
        definition.build_definition(
            hass, pages + [{"id": "loop", "title": "Loop", "parent": "loop"}], "ember"
        )
    deep = definition.build_definition(
        hass,
        [
            {"id": str(i), "title": "Demo", "parent": str(i - 1) if i else ""}
            for i in range(9)
        ],
        "ember",
    )
    page = deep["tree"]
    for i in range(1, 9):
        page = page["items"][0] if "items" in page else page["children"][0]
        assert page["id"] == str(i)


def test_navigation_ids_survive_reordering_and_long_root(dial):
    nav = dial.load("navigator").Navigator
    children = [
        {"id": "a", "label": "A", "children": []},
        {
            "id": "b",
            "label": "B",
            "children": [{"id": "lamp", "label": "Lamp", "entity_id": "light.example"}],
        },
    ]
    tree = {"id": "r" * 64, "title": "Home", "items": children}
    before = nav(definition={"tree": tree})
    before.input("touch", "b")
    before.input("press")
    after = nav(definition={"tree": {**tree, "items": children[::-1]}})
    after.restore(before)
    assert after.current()["entity_id"] == "light.example"
    assert after.input("back")["title"] == "B"
    assert len(after.views) == 3
    assert after.input("back")["selected"] == 0


def test_all_supported_scenes_fit_device_contract(dial):
    scene = dial.load("scene")
    nav_type = dial.load("navigator").Navigator
    protocol = dial.load("protocol")
    maximum = 0
    for theme in scene.THEMES:
        for count in range(9):
            for domain in ("page", "light", "switch", "cover"):
                menus = domain == "page"
                items = [
                    {
                        "id": f"item_{i}",
                        "label": "Wide Demo Label " * 4,
                        **(
                            {"children": []}
                            if menus
                            else {"entity_id": f"{domain}.demo_{i}"}
                        ),
                    }
                    for i in range(count)
                ]
                nav = nav_type(
                    definition={
                        "tree": {
                            "id": "root",
                            "title": "A wide page title",
                            "theme": theme,
                            "items": items,
                        }
                    }
                )
                root = nav.current()
                for view in (root, nav.input("press")):
                    if view.get("domain") == "cover":
                        view.update(continuous=True, actions=["open", "stop", "close"])
                    payload = json.loads(
                        protocol.device_payload(view, nav.previous(), 100)
                    )
                    encoded = json.dumps(payload, separators=(",", ":")).encode()
                    maximum = max(maximum, len(encoded))
                    assert len(encoded) <= scene.MAX_VIEW_BYTES
                    for resolved in (payload["scene"], payload.get("previous")):
                        if not resolved:
                            continue
                        assert len(resolved["elements"]) <= 64
                        assert len(resolved["regions"]) <= 16
                        for element in resolved["elements"]:
                            if element["op"] == "mask":
                                assert (
                                    len(element["pixels"])
                                    == ((element["width"] * element["height"] + 3) // 4)
                                    * 2
                                )
    assert (
        maximum > 8192
    )  # Exercise the reviewed overflow case, within the new measured bound.


def test_light_identity_power_availability_and_complete_text(dial):
    scene = dial.load("scene")
    view = {
        "kind": "control",
        "id": "demo",
        "title": "Demo lamp",
        "style": "CTL-LIGHT-INSTRUMENT",
        "value": 100,
        "active": True,
        "available": True,
    }
    original = scene.compile_scene(view)
    for change in ({"title": "Other lamp"}, {"active": False}, {"available": False}):
        assert scene.compile_scene({**view, **change}) != original
    mask = dial.load("assets")._text_mask("100", 30, "#ffffff")
    assert 40 < mask["width"] < 60
    assert 18 < mask["height"] < 30
    assert any(
        int(mask["pixels"][i : i + 2], 16) for i in range(0, len(mask["pixels"]), 2)
    )


def test_mixed_domain_tree_and_template_defaults(dial):
    definition = dial.load("definition")
    nav_type = dial.load("navigator").Navigator
    protocol = dial.load("protocol")
    hass = SimpleNamespace(states={})
    pages = [
        {"id": "root", "title": "Home"},
        {"id": "floor", "title": "Floor", "parent": "root", "theme": "cobalt"},
        {
            "id": "room",
            "title": "Room",
            "parent": "floor",
            "theme": "verdant",
            "lights": ["light.demo"],
            "entities": ["switch.demo", "cover.demo"],
        },
    ]
    result = definition.build_definition(hass, pages, "ember")
    for item in definition.leaf_items(result["tree"]):
        domain = item["entity_id"].partition(".")[0]
        assert (item["profile"], item["style"]) == definition.CONTROL_TYPES[domain][:2]
    nav = nav_type(definition=result)
    nav.input("press")
    nav.input("press")
    assert nav.current()["theme"] == "verdant"
    for domain in ("light", "switch", "cover"):
        view = nav.input("touch", domain + ".demo")
        assert view["domain"] == domain
        assert view["theme"] == "verdant"
        view.update(
            continuous=domain != "switch",
            actions=["open", "stop", "close"] if domain == "cover" else [],
        )
        payload = json.loads(protocol.device_payload(view, nav.previous(), 1))
        assert ("value" in payload) == (domain != "switch")
        assert "entity_id" not in payload
        assert len(payload["scene"]["elements"]) <= 64
        nav.input("back")
    for domain in ("switch", "cover"):
        tree = {
            "id": "root",
            "title": "Home",
            "items": [{"id": "demo", "label": "Demo", "entity_id": domain + ".demo"}],
        }
        definition.validate_definition({"tree": tree})
        view = nav_type(definition={"tree": tree}).input("press")
        assert view["style"] == definition.CONTROL_TYPES[domain][1]
    with pytest.raises(ValueError, match="supported HA entity"):
        definition.build_definition(
            hass,
            [{"id": "root", "title": "Home", "entities": ["camera.demo"]}],
            "ember",
        )
    with pytest.raises(ValueError, match="lists"):
        definition.build_definition(
            hass, [{"id": "root", "title": "Home", "entities": "switch.demo"}], "ember"
        )
