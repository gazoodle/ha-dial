import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest


def load():
    path = Path(__file__).parents[1] / "tools/ux-gallery/server.py"
    spec = importlib.util.spec_from_file_location("ha_dial_gallery_server", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_device_url_accepts_local_targets_and_rejects_urls():
    server = load()

    assert server.device_url("ha-dial.local") == "http://ha-dial.local/ha-dial/atlas-frame"
    assert server.device_url("192.168.1.20:8080") == "http://192.168.1.20:8080/ha-dial/atlas-frame"
    with pytest.raises(ValueError):
        server.device_url("http://example.com")


def test_forward_frame_sends_exact_rgb565_body():
    server = load()
    frame = bytes(server.FRAME_BYTES)

    with patch.object(server, "urlopen") as open_url:
        open_url.return_value.__enter__.return_value.status = 200
        open_url.return_value.__enter__.return_value.read.return_value = b'{"ok":true}'
        assert server.forward_frame("ha-dial.local", frame) == (200, '{"ok":true}')
        request = open_url.call_args.args[0]
        assert request.full_url == "http://ha-dial.local/ha-dial/atlas-frame"
        assert request.data == frame

    with pytest.raises(ValueError):
        server.forward_frame("ha-dial.local", b"short")
