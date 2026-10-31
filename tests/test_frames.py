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


def page(style="CAM-PORTAL", **clock):
    return {"id": "gate", "kind": "menu", "title": "Example", "items": [], "style": style, "clock": {"image_entity": "camera.example", **clock}}


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
        frames.request_frame(hass, "dial", view, publish)  # Coming back counts as entering.
        await settle()
        assert len(camera.calls) == 3

    asyncio.run(run())


def test_camera_state_is_not_a_trigger_but_an_image_entity_is(integration, dial):
    clock = dial.load("chronograph")
    # A camera's state event fires when its access token rotates, which would be a hidden timer.
    assert clock.source_entities(page()) == set()
    assert clock.source_entities(page(image_entity="image.example")) == {"image.example"}
    assert clock.source_entities(page(refresh_entity="event.bell", detection_entity="binary_sensor.person")) == {"event.bell", "binary_sensor.person"}
    with pytest.raises(ValueError):
        clock.validate_clock({"image_entity": "light.example"})


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
        view = page(image_entity=f"camera.example_{index}")
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
