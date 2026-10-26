import importlib.util
import json
from pathlib import Path


def load():
    path = Path(__file__).parents[1] / "custom_components/ha_dial/pill.py"
    spec = importlib.util.spec_from_file_location("ha_dial_pill", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_pill_is_antialiased_and_fits_view_message():
    pill = load().render_pill("Demo light")

    assert pill["height"] == 22
    assert pill["width"] <= 150
    assert len(pill["pixels"]) == pill["width"] * pill["height"]
    assert {"0", "2", "f"} <= set(pill["pixels"])
    assert len(json.dumps({"title": "Demo light", "pill": pill})) < 4096


def test_long_name_is_truncated_to_transport_limit():
    pill = load().render_pill("A very long invented light name that cannot possibly fit")

    assert pill["width"] <= 150
    assert len(pill["pixels"]) == pill["width"] * 22
