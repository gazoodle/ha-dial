"""Mirror HA Dial into a Home Assistant config folder."""

from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

SOURCE = Path(__file__).parents[1] / "custom_components" / "ha_dial"
sys.path.insert(0, str(SOURCE))
from deployment import MARKER, files, manifest_version, revision

_LOGGER = logging.getLogger(__name__)


def install(source: Path, destination: Path) -> str:
    first_install = not destination.exists()
    previous_version = manifest_version(destination)
    wanted = files(source)
    changed = False

    for relative, path in wanted.items():
        target = destination / relative
        if target.exists() and target.read_bytes() == path.read_bytes():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        changed = True

    if destination.exists():
        for relative in set(files(destination)) - set(wanted):
            (destination / relative).unlink()
            changed = True
        for folder in sorted(destination.rglob("*"), reverse=True):
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()

    status = "installed" if first_install else "updated" if changed else "current"
    if changed:
        marker = {
            "status": status,
            "from_version": previous_version,
            "to_version": manifest_version(source),
            "to_revision": revision(source),
        }
        (destination / MARKER).write_text(json.dumps(marker) + "\n", "utf-8")
    return status


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("usage: tools/deploy.py HA_CONFIG_FOLDER")
    config = Path(argv[0]).expanduser()
    if not config.is_dir():
        raise SystemExit(f"Home Assistant config folder does not exist: {config}")

    destination = config / "custom_components" / "ha_dial"
    status = install(SOURCE, destination)
    _LOGGER.info("HA Dial integration: %s at %s", status, destination)
    if status == "installed":
        _LOGGER.info("Restart Home Assistant once, then add the HA Dial integration")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
