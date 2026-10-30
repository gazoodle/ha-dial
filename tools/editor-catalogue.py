"""Regenerate the browser's selector catalogue from HA's authoritative catalogue."""

import json
import runpy
from pathlib import Path

root = Path(__file__).resolve().parents[1]
catalogue = runpy.run_path(str(root / "custom_components/ha_dial/catalogue.py"))
exports = {
    "DOMAINS": list(catalogue["CONTROL_TYPES"]),
    "NAV_STYLES": sorted(catalogue["PAGE_STYLES"]),
    "CONTROL_STYLES": {
        domain: sorted(catalogue["control_styles"](domain))
        for domain in catalogue["CONTROL_TYPES"]
    },
}
(root / "custom_components/ha_dial/www/editor/catalogue.js").write_text(
    "// Generated from catalogue.py; refresh with tools/editor-catalogue.py.\n"
    + "".join(
        f"export const {name} = {json.dumps(value)};\n"
        for name, value in exports.items()
    )
)
