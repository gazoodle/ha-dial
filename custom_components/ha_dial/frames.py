"""Camera and photo frames: captured and treated in HA, then fetched raw by the Dial.

The Dial gets a short-lived URL that reaches one frame and nothing else, so it never holds an HA
token and frames never go through the JSON scene. Capture happens on entering a page and on events
from bound entities. There is no timer: a stale picture shows its age instead.
"""

import base64
import logging
import secrets
import zlib
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import BytesIO

from .catalogue import CAMERA_STYLES, IMAGE_STYLES
from .const import DOMAIN
from .scene import view_theme

_LOGGER = logging.getLogger(__name__)
FRAME_PATH = "/api/ha_dial/frame"
TOKEN_LIFETIME = timedelta(minutes=5)
KEEP_FRAMES = 4  # One per visible page per Dial is enough; this bounds HA's memory, not the Dial's.
MAX_FRAME_BYTES = 32768  # Mirrors the firmware's fixed buffer.
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
# Each style's drawn size is its own: width x height x 2 must fit the Dial's buffer.
SPECS = {
    "CAM-PORTAL": {"width": 144, "height": 112, "scale": 1, "radius": 16, "treatment": "portal"},
    "CAM-CINEMA": {"width": 164, "height": 96, "scale": 1, "radius": 5, "treatment": "cinema"},
    "CAM-RADAR": {"width": 128, "height": 128, "scale": 1, "radius": 16, "treatment": "radar"},
    "WAT-PHOTOS": {"width": 120, "height": 120, "scale": 2, "radius": 0, "treatment": "photo"},
}


@dataclass
class Frame:
    """A treated frame; the token lapses by itself, so an old URL can't be replayed for long."""

    data: bytes
    crc: int
    width: int
    height: int
    scale: int
    captured: datetime
    encoded: str = field(repr=False)
    token: str = ""
    issued: datetime | None = None


def _rgb(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def rgb565(image) -> bytes:
    """Big-endian RGB565, which both renderers read."""
    source = image.convert("RGB").tobytes()
    out = bytearray(len(source) // 3 * 2)
    for index in range(len(source) // 3):
        r, g, b = source[index * 3], source[index * 3 + 1], source[index * 3 + 2]
        value = (r >> 3) << 11 | (g >> 2) << 5 | b >> 3
        out[index * 2], out[index * 2 + 1] = value >> 8, value & 0xFF
    return bytes(out)


def render_frame(raw: bytes, spec: dict, theme: dict, crisp: bool) -> bytes:
    """Crop and treat a picture. Blocking: run it in an executor."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps

    image = ImageOps.exif_transpose(Image.open(BytesIO(raw))).convert("RGB")
    image = ImageOps.fit(image, (spec["width"], spec["height"]), Image.Resampling.LANCZOS)
    treatment = spec["treatment"]
    if treatment in {"portal", "radar"}:
        image = ImageEnhance.Contrast(ImageOps.grayscale(image).convert("RGB")).enhance(1.12 if treatment == "portal" else 1.18)
    elif treatment == "cinema":
        image = ImageEnhance.Contrast(ImageEnhance.Color(image).enhance(1.08)).enhance(1.04)
    if treatment == "photo":
        # Darken towards the bottom, where the time sits on the photograph.
        shade = Image.linear_gradient("L").resize(image.size)
        shade = shade.point(lambda value: max(0, (value - 90) * 220 // 165))
        image = Image.composite(Image.new("RGB", image.size, (0, 0, 0)), image, shade)

    if crisp:
        # Ordered dither to two colours: at this resolution it reads as line-step texture.
        ink = _rgb(theme["primary"] if treatment == "radar" else theme["secondary"])
        ground = _rgb(theme["bg"])
        gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=2)
        pixels = gray.load()
        image = Image.new("RGB", gray.size, ground)
        target = image.load()
        for y in range(gray.height):
            for x in range(gray.width):
                if pixels[x, y] * 17 // 256 > BAYER[y % 4][x % 4]:
                    target[x, y] = ink
    elif treatment == "radar":
        image = Image.blend(image, Image.new("RGB", image.size, _rgb(theme["primary"])), 0.22)

    if spec["radius"]:
        # Rounded corners are baked in: the Dial only ever blits a rectangle.
        mask = Image.new("L", (image.width * 4, image.height * 4))
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, mask.width - 1, mask.height - 1), spec["radius"] * 4, fill=255)
        image = Image.composite(image, Image.new("RGB", image.size, _rgb(theme["bg"])), mask.resize(image.size, Image.Resampling.NEAREST if crisp else Image.Resampling.LANCZOS))
    data = rgb565(image)
    if len(data) > MAX_FRAME_BYTES:
        raise ValueError(f"Frame of {len(data)} bytes exceeds {MAX_FRAME_BYTES}")
    return data


def frame_key(view: dict) -> tuple | None:
    """What makes a frame distinct; a theme or mode change needs a new treatment."""
    style = view.get("style")
    if style in CAMERA_STYLES:
        entity = view.get("entity_id", "")
        if entity.partition(".")[0] not in {"camera", "image"}:
            return None
    else:
        entity = view.get("clock", {}).get("image_entity")
    if style not in IMAGE_STYLES or not entity:
        return None
    theme, options = view_theme(view)
    return (entity, style, theme["primary"], theme["secondary"], theme["bg"], options["raster"])


async def _source_image(hass, entity: str) -> bytes:
    if entity.startswith("camera."):
        from homeassistant.components.camera import async_get_image
    else:
        from homeassistant.components.image import async_get_image
    return (await async_get_image(hass, entity)).content


async def capture(hass, view: dict, key: tuple) -> None:
    """Fetch and treat one frame. A failure keeps the last good picture and says why."""
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.util import dt as dt_util

    state = hass.data[DOMAIN]
    frames = state.setdefault("frames", OrderedDict())
    errors = state.setdefault("frame_errors", {})
    spec = SPECS[view["style"]]
    theme, options = view_theme(view)
    try:
        raw = await _source_image(hass, key[0])
        data = await hass.async_add_executor_job(render_frame, raw, spec, theme, options["raster"] == "crisp")
    except (HomeAssistantError, OSError, TimeoutError, ValueError) as error:
        _LOGGER.warning("Could not capture %s for the Dial: %s", key[0], error)
        errors[key] = "NO IMAGE"
        return
    errors.pop(key, None)
    frames[key] = Frame(
        data, zlib.crc32(data), spec["width"], spec["height"], spec["scale"], dt_util.utcnow(), base64.b64encode(data).decode()
    )
    frames.move_to_end(key)
    while len(frames) > KEEP_FRAMES:
        frames.popitem(last=False)


def request_frame(hass, device: str, view: dict, publish) -> None:
    """Capture when a page is entered or a bound entity fires, without delaying the scene.

    Navigation must stay immediate, so the page publishes now and again when its picture is ready.
    """
    state = hass.data[DOMAIN]
    visits = state.setdefault("frame_visits", {})
    key = frame_key(view)
    if key is None:
        visits.pop(device, None)
        return
    entered = visits.get(device) != key
    visits[device] = key
    dirty = state.setdefault("frame_dirty", set())
    stale = key[0] in dirty or view.get("clock", {}).get("refresh_entity") in dirty
    known = key in state.get("frames", {}) or key in state.get("frame_errors", {})
    tasks = state.setdefault("frame_tasks", {})
    if not (entered or stale or not known) or device in tasks:
        return
    dirty.discard(key[0])
    dirty.discard(view.get("clock", {}).get("refresh_entity"))

    async def work():
        try:
            await capture(hass, view, key)
        finally:
            tasks.pop(device, None)
        await publish()

    # Stored before it runs: the task removes itself, and must not finish before it is recorded.
    tasks[device] = hass.async_create_task(work(), eager_start=False)


def mark_stale(hass, entity: str) -> None:
    # A camera's own state event fires when its access token rotates, so it would act as a timer.
    if entity.startswith("camera."):
        return
    hass.data[DOMAIN].setdefault("frame_dirty", set()).add(entity)


def cancel_capture(hass, device: str) -> None:
    if task := hass.data[DOMAIN].get("frame_tasks", {}).pop(device, None):
        task.cancel()


def _device_url(hass, token: str) -> str:
    """The Dial has no TLS trust store, so it needs HA's plain local address."""
    from homeassistant.helpers.network import NoURLAvailableError, get_url

    try:
        base = get_url(hass, allow_external=False, allow_cloud=False, prefer_external=False)
    except NoURLAvailableError:
        _LOGGER.warning("HA has no internal URL, so the Dial can't fetch images")
        return ""
    if not base.startswith("http://"):
        _LOGGER.warning("HA's internal URL is not plain HTTP, so the Dial can't fetch images")
        return ""
    return f"{base}{FRAME_PATH}/{token}"


def _age(captured: datetime, now: datetime) -> str:
    minutes = int((now - captured).total_seconds() // 60)
    if minutes < 1:
        return "NOW"
    if minutes < 60:
        return f"{minutes} MIN"
    return f"{minutes // 60} HR"


def resolve_frame(hass, view: dict) -> dict | None:
    """The image for this page right now, or None for a page that has no source."""
    key = frame_key(view)
    if key is None:
        return None
    from homeassistant.util import dt as dt_util

    state = hass.data.get(DOMAIN, {})
    frame = state.get("frames", {}).get(key)
    if frame is None:
        return {"error": state.get("frame_errors", {}).get(key, "LOADING")}
    now = dt_util.utcnow()
    if frame.issued is None or now - frame.issued >= TOKEN_LIFETIME:
        frame.token, frame.issued = secrets.token_urlsafe(24), now
    url = _device_url(hass, frame.token)
    return {
        "url": url, "crc": frame.crc, "width": frame.width, "height": frame.height, "scale": frame.scale,
        "age": _age(frame.captured, now), "error": state.get("frame_errors", {}).get(key) or (None if url else "NO LINK"),
    }


def scene_frames(hass, scene: dict) -> dict:
    """The browser's copy of any frame this scene draws; browsers don't fetch the Dial's URL."""
    wanted = {element["crc"] for element in scene["elements"] if element["op"] == "image"}
    if not wanted:
        return {}
    known = hass.data.get(DOMAIN, {}).get("frames", {}).values()
    return {str(frame.crc): frame.encoded for frame in known if frame.crc in wanted}


def frame_for_token(hass, token: str) -> Frame | None:
    """The live frame this token opens, if any. The token is the only key to it."""
    from homeassistant.util import dt as dt_util

    now = dt_util.utcnow()
    for frame in hass.data.get(DOMAIN, {}).get("frames", {}).values():
        if frame.token and secrets.compare_digest(frame.token, token) and frame.issued and now - frame.issued < TOKEN_LIFETIME:
            return frame
    return None
