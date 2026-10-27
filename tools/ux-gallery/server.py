#!/usr/bin/env python3
"""Serve the UX atlas and proxy one raw frame to a local HA Dial."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
FRAME_BYTES = 240 * 240 * 2
HOST = re.compile(r"[A-Za-z0-9.-]+(?::([0-9]{1,5}))?")


def device_url(host: str) -> str:
    host = host.strip()
    match = HOST.fullmatch(host)
    if not match or (match.group(1) and int(match.group(1)) > 65535):
        raise ValueError("Enter a hostname or IPv4 address, optionally with a port")
    return f"http://{host}/ha-dial/atlas-frame"


def forward_frame(host: str, frame: bytes) -> tuple[int, str]:
    if len(frame) != FRAME_BYTES:
        raise ValueError(f"Expected {FRAME_BYTES} RGB565 bytes")
    request = Request(
        device_url(host),
        data=frame,
        method="POST",
        headers={"Content-Type": "application/octet-stream"},
    )
    with urlopen(request, timeout=20) as response:
        return response.status, response.read().decode("utf-8")


class AtlasHandler(SimpleHTTPRequestHandler):
    def reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/push":
            self.reply(404, {"ok": False, "error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length != FRAME_BYTES:
                raise ValueError(f"Expected {FRAME_BYTES} RGB565 bytes")
            host = parse_qs(parsed.query).get("host", [""])[0]
            status, body = forward_frame(host, self.rfile.read(length))
            self.reply(status, json.loads(body))
        except (ValueError, json.JSONDecodeError) as error:
            self.reply(400, {"ok": False, "error": str(error)})
        except HTTPError as error:
            self.reply(error.code, {"ok": False, "error": error.read().decode() or str(error)})
        except (URLError, TimeoutError) as error:
            self.reply(502, {"ok": False, "error": f"Dial unavailable: {getattr(error, 'reason', error)}"})


if __name__ == "__main__":
    print("HA Dial UX Atlas: http://127.0.0.1:4173/tools/ux-gallery/")
    ThreadingHTTPServer(
        ("127.0.0.1", 4173), partial(AtlasHandler, directory=ROOT)
    ).serve_forever()
