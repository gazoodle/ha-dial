"""The one HTTP endpoint the Dial reads, for raw image frames."""

from homeassistant.components.http import HomeAssistantView

from .frames import FRAME_PATH, frame_for_token


class FrameView(HomeAssistantView):
    """Unauthenticated by design: an unguessable, expiring token opens one frame and nothing else."""

    url = FRAME_PATH + "/{token}"
    name = "api:ha_dial:frame"
    requires_auth = False

    def __init__(self, hass) -> None:
        self.hass = hass

    async def get(self, request, token: str):
        from aiohttp import web

        frame = frame_for_token(self.hass, token)
        if frame is None:
            return web.Response(status=404)
        return web.Response(body=frame.data, content_type="application/octet-stream")
