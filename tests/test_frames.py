"""Camera and photo frames: treatment, capture rules, expiry and failure."""

import asyncio
import re
import zlib
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RED = (255, 0, 0)


def png(colour=RED, size=(300, 200)):
    out = BytesIO()
    Image.new("RGB", size, colour).save(out, "PNG")
    return out.getvalue()


def page(style="CAM-PORTAL", entity="camera.example", **clock):
    return {"id": "control:" + entity, "kind": "control", "entity_id": entity, "title": "Example", "items": [], "style": style, "clock": clock}


@pytest.fixture
def camera(integration, dial, monkeypatch):
    """A fake camera, recording each capture and able to fail on demand."""
    source = SimpleNamespace(calls=[], fail=False)

    async def get_image(_hass, entity):
        source.calls.append(entity)
        if source.fail:
            raise integration.hass_error("camera offline")
        return SimpleNamespace(content=png())

    errors = __import__("sys").modules["homeassistant.exceptions"]
    integration.hass_error = errors.HomeAssistantError
    dial.module("homeassistant.components.camera", async_get_image=get_image)
    dial.module("homeassistant.components.image", async_get_image=get_image)

    class NoURLAvailableError(Exception):
        pass

    source.url = "http://ha.invalid:8123"
    dial.module("homeassistant.helpers.network", NoURLAvailableError=NoURLAvailableError, get_url=lambda *_a, **_k: source.url)

    async def executor(job, *args):
        return job(*args)

    integration.hass.async_add_executor_job = executor
    return source


def test_every_style_fits_the_dial_buffer_and_treatments_differ(dial):
    frames = dial.load("frames")
    theme = dial.load("scene").THEMES["ember"]
    firmware = int(re.search(r"MAX_FRAME_BYTES = (\d+)", (ROOT / "components/ha_dial/scene.h").read_text()).group(1))
    assert frames.MAX_FRAME_BYTES == firmware
    made = []
    for spec in frames.SPECS.values():
        assert spec["width"] * spec["height"] * 2 <= firmware
        for crisp in (False, True):
            data = frames.render_frame(png((90, 140, 200)), spec, theme, crisp)
            assert len(data) == spec["width"] * spec["height"] * 2
            made.append(data)
    assert len(set(made)) == len(made)


def test_rgb565_is_big_endian_and_crisp_is_two_colours(dial):
    frames = dial.load("frames")
    theme = dial.load("scene").THEMES["ember"]
    assert frames.rgb565(Image.new("RGB", (1, 1), (255, 0, 0))) == b"\xf8\x00"
    gradient = Image.linear_gradient("L").resize((200, 200)).convert("RGB")
    out = BytesIO()
    gradient.save(out, "PNG")
    data = frames.render_frame(out.getvalue(), frames.SPECS["CAM-CINEMA"], theme, True)
    assert len({data[i : i + 2] for i in range(0, len(data), 2)}) == 2
    # Rounded corners are baked in as the page background, because the Dial only blits rectangles.
    assert data[:2] == frames.rgb565(Image.new("RGB", (1, 1), frames._rgb(theme["bg"])))


def test_capture_on_entry_and_events_never_on_republish(integration, dial, camera):
    frames = dial.load("frames")
    hass = integration.hass
    published = []

    async def publish():
        published.append(1)

    async def settle():
        for task in list(hass.data["ha_dial"].get("frame_tasks", {}).values()):
            await task

    async def run():
        view = page(refresh_entity="binary_sensor.gate_motion")
        frames.request_frame(hass, "dial", view, publish)
        assert hass.data["ha_dial"]["frame_tasks"]  # The page publishes without waiting for the picture.
        await settle()
        assert camera.calls == ["camera.example"] and published == [1]
        for _ in range(3):  # Minute ticks and rotary redraws republish the page.
            frames.request_frame(hass, "dial", view, publish)
        await settle()
        assert len(camera.calls) == 1
        frames.mark_stale(hass, "binary_sensor.gate_motion")
        frames.request_frame(hass, "dial", view, publish)
        await settle()
        assert len(camera.calls) == 2
        frames.request_frame(hass, "dial", {"id": "nav", "style": "NAV-ORBIT"}, publish)
        assert frames.frame_key({**view, "entity_id": "light.example"}) is None
        frames.request_frame(hass, "dial", view, publish)  # Coming back counts as entering.
        await settle()
        assert len(camera.calls) == 3

    asyncio.run(run())


def test_camera_state_is_not_a_trigger_but_an_image_entity_is(integration, dial):
    clock = dial.load("chronograph")
    frames = dial.load("frames")
    # A camera's state event fires when its access token rotates, which would be a hidden timer.
    frames.mark_stale(integration.hass, "camera.example")
    assert "camera.example" not in integration.hass.data["ha_dial"].get("frame_dirty", set())
    frames.mark_stale(integration.hass, "image.example")
    assert "image.example" in integration.hass.data["ha_dial"]["frame_dirty"]
    assert clock.source_entities(page(refresh_entity="event.bell", detection_entity="binary_sensor.person")) == {"event.bell", "binary_sensor.person"}
    photos = {"style": "WAT-PHOTOS", "clock": {"image_entity": "image.example"}}
    assert clock.source_entities(photos) == {"image.example"}
    with pytest.raises(ValueError):
        clock.validate_clock({"image_entity": "light.example"})
    with pytest.raises(ValueError):
        clock.validate_clock({"action_entities": ["light.a", "light.b", "light.c"]})


def test_failure_keeps_the_last_picture_and_does_not_retry_in_a_loop(integration, dial, camera, caplog):
    frames = dial.load("frames")
    hass = integration.hass
    view = page()
    key = frames.frame_key(view)

    async def publish():
        pass

    async def settle():
        for task in list(hass.data["ha_dial"].get("frame_tasks", {}).values()):
            await task

    async def run():
        camera.fail = True
        frames.request_frame(hass, "dial", view, publish)
        await settle()
        assert frames.resolve_frame(hass, view) == {"error": "NO IMAGE"}
        assert "camera offline" in caplog.text
        frames.request_frame(hass, "dial", view, publish)
        await settle()
        assert len(camera.calls) == 1
        camera.fail = False
        await frames.capture(hass, view, key)
        good = frames.resolve_frame(hass, view)
        assert good["error"] is None and good["crc"] == zlib.crc32(hass.data["ha_dial"]["frames"][key].data)
        camera.fail = True
        await frames.capture(hass, view, key)
        kept = frames.resolve_frame(hass, view)
        assert kept["crc"] == good["crc"] and kept["error"] == "NO IMAGE"

    asyncio.run(run())


def test_tokens_expire_open_one_frame_and_need_plain_http(integration, dial, camera, monkeypatch):
    frames = dial.load("frames")
    hass = integration.hass
    view = page()
    key = frames.frame_key(view)
    asyncio.run(frames.capture(hass, view, key))
    image = frames.resolve_frame(hass, view)
    token = image["url"].rsplit("/", 1)[1]
    assert image["url"].startswith("http://ha.invalid:8123/api/ha_dial/frame/")
    assert frames.frame_for_token(hass, token).crc == image["crc"]
    assert frames.frame_for_token(hass, "guess") is None
    frame = hass.data["ha_dial"]["frames"][key]
    frame.issued -= frames.TOKEN_LIFETIME + timedelta(seconds=1)
    assert frames.frame_for_token(hass, token) is None
    renewed = frames.resolve_frame(hass, view)
    assert renewed["url"] != image["url"] and renewed["crc"] == image["crc"]
    camera.url = "https://ha.invalid"
    assert frames.resolve_frame(hass, view)["error"] == "NO LINK"


def test_held_frames_are_bounded_and_scenes_declare_version_six(integration, dial, camera):
    frames, scene = dial.load("frames"), dial.load("scene")
    hass = integration.hass
    for index in range(frames.KEEP_FRAMES + 3):
        view = page(entity=f"camera.example_{index}")
        asyncio.run(frames.capture(hass, view, frames.frame_key(view)))
    assert len(hass.data["ha_dial"]["frames"]) == frames.KEEP_FRAMES
    view = page()
    asyncio.run(frames.capture(hass, view, frames.frame_key(view)))
    clock = {"hour": 1, "minute": 2, "date": "X", "image": frames.resolve_frame(hass, view), "detection": None}
    drawn = scene.compile_scene({**view, "_clock": clock})
    assert drawn["version"] == 6
    assert frames.scene_frames(hass, drawn).keys() == {str(clock["image"]["crc"])}
    missing = scene.compile_scene({**view, "_clock": {**clock, "image": {"error": "NO IMAGE"}}})
    assert missing["version"] == 5 and frames.scene_frames(hass, missing) == {}


def camera_definition(integration, dial, **clock):
    definition = dial.load("definition")
    pages = [{"id": "root", "title": "Home", "entities": [{"entity_id": "camera.gate", "style": "CAM-PORTAL", "clock": clock}, "light.example"]}]
    return definition.build_definition(integration.hass, pages, "ember")


def test_a_camera_is_an_entity_and_its_faces_are_not_page_styles(integration, dial):
    catalogue, definition = dial.load("catalogue"), dial.load("definition")
    assert catalogue.CONTROL_TYPES["camera"][1] == "CAM-PORTAL"
    assert catalogue.control_styles("camera") == catalogue.control_styles("image") == catalogue.CAMERA_STYLES
    assert not catalogue.PAGE_STYLES & catalogue.CAMERA_STYLES
    assert "WAT-PHOTOS" in catalogue.PAGE_STYLES
    with pytest.raises(ValueError):
        definition.build_definition(integration.hass, [{"id": "root", "title": "Home", "style": "CAM-PORTAL"}], "ember")
    with pytest.raises(ValueError):
        camera_definition(integration, dial, action_entities=["camera.other"])
    view = dial.load("navigator").Navigator(definition=camera_definition(integration, dial)).input("press")
    assert (view["kind"], view["style"], view["entity_id"]) == ("control", "CAM-PORTAL", "camera.gate")
    drawn = dial.load("scene").compile_scene({**view, "_clock": {"hour": 1, "minute": 2, "date": "X", "image": {"error": "NO IMAGE"}}})
    assert {region["id"] for region in drawn["regions"]} == {"back", "home"}


def test_a_camera_button_opens_its_control_and_back_returns_to_the_camera(integration, dial):
    nav = dial.load("navigator").Navigator(definition=camera_definition(integration, dial, action_entities=["light.example", "switch.example"]))
    camera = nav.input("press")
    assert [item["id"] for item in camera["items"]] == ["light.example", "switch.example"]
    assert nav.input("rotate_right")["selected"] == 1
    assert nav.input("rotate_right")["selected"] == 0
    opened = nav.input("press")
    assert opened["entity_id"] == "light.example"
    assert nav.previous()["entity_id"] == "camera.gate"
    assert nav.input("back")["entity_id"] == "camera.gate"
    assert nav.input("touch", "switch.example")["entity_id"] == "switch.example"
    assert nav.input("home")["kind"] == "menu" and nav.control_parent is None
    nav.input("press")
    assert nav.input("back")["kind"] == "menu"


def test_opening_a_control_from_a_camera_does_not_operate_it(integration, dial, camera):
    runtime = dial.load("runtime")
    hass = integration.hass
    definition = camera_definition(integration, dial, action_entities=["light.example"])

    async def run():
        await runtime._install_definition(hass, "dial", {"pages": []}, definition)
        await runtime._input(hass, "dial", "press")
        for task in list(hass.data["ha_dial"].get("frame_tasks", {}).values()):
            await task
        opened = await runtime._input(hass, "dial", "press")
        assert opened["entity_id"] == "light.example"
        light_calls = [call for call in hass.services.async_call.call_args_list if call.args[0] == "light"]
        assert not light_calls, "pressing a camera's button must only open the control"
        await runtime._input(hass, "dial", "press")
        assert any(call.args[0] == "light" for call in hass.services.async_call.call_args_list)
        hass.data["ha_dial"]["definition_unsubs"].pop("dial")()

    asyncio.run(run())


def test_the_gallery_offers_a_cameras_styles_with_its_picture(integration, dial, camera):
    hass, connection = integration.hass, integration.connection

    async def run():
        await integration.code._ws_gallery(hass, connection, {
            "id": 1, "page": {"title": "Home", "entities": ["camera.gate"]}, "entity": "camera.gate", "theme": "ember",
        })

    asyncio.run(run())
    connection.send_error.assert_not_called()
    result = connection.send_result.call_args.args[1]
    catalogue = dial.load("catalogue")
    assert set(result["styles"]) == catalogue.CAMERA_STYLES
    for scene in result["styles"].values():
        crc = next(element["crc"] for element in scene["elements"] if element["op"] == "image")
        assert str(crc) in result["frames"]
