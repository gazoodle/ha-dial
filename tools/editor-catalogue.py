"""Regenerate the browser's selector catalogue from HA's authoritative tables."""

import json
import runpy
from pathlib import Path

root = Path(__file__).resolve().parents[1]
catalogue = runpy.run_path(str(root / "custom_components/ha_dial/catalogue.py"))
appearance = runpy.run_path(str(root / "custom_components/ha_dial/appearance.py"))
styles = sorted(catalogue["STYLES"])
settings = {
    **{name: {"group": s[0], "label": s[1], "kind": "number", "low": s[2], "high": s[3]} for name, s in appearance["NUMBERS"].items()},
    **{name: {"group": s[0], "label": s[1], "kind": "toggle"} for name, s in appearance["TOGGLES"].items()},
    **{name: {"group": s[0], "label": s[1], "kind": "choice", "choices": list(s[2])} for name, s in appearance["CHOICES"].items()},
}
exports = {
    "DOMAINS": list(catalogue["CONTROL_TYPES"]),
    "NAV_STYLES": sorted(catalogue["PAGE_STYLES"]),
    "CONTROL_STYLES": {
        domain: sorted(catalogue["control_styles"](domain))
        for domain in catalogue["CONTROL_TYPES"]
    },
    "DEFAULT_STYLES": {domain: spec[1] for domain, spec in catalogue["CONTROL_TYPES"].items()},
    "FACE_SOURCES": catalogue["FACE_SOURCES"],
    "SETTINGS": settings,
    "DEFAULTS": appearance["DEFAULTS"],
    "CRISP_DEFAULTS": appearance["CRISP_DEFAULTS"],
    "CRISP_HIDDEN": sorted(appearance["CRISP_HIDDEN"]),
    "PICTURE_DEFAULTS": appearance["PICTURE_DEFAULTS"],
    "REQUIRES": appearance["REQUIRES"],
    "STYLE_SETTINGS": {style: list(appearance["style_settings"](style)) for style in styles},
}
(root / "custom_components/ha_dial/www/editor/catalogue.js").write_text(
    "// Generated from catalogue.py and appearance.py; refresh with tools/editor-catalogue.py.\n"
    + "".join(
        f"export const {name} = {json.dumps(value)};\n"
        for name, value in exports.items()
    )
)
