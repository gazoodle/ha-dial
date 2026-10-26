"""Shared deployment marker format; imports no Home Assistant modules."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

MARKER = ".restart_required.json"


def files(folder: Path) -> dict[Path, Path]:
    return {
        path.relative_to(folder): path
        for path in folder.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name not in {MARKER, ".DS_Store"}
        and path.suffix not in {".pyc", ".pyo"}
    }


def manifest_version(folder: Path) -> str | None:
    try:
        value = json.loads((folder / "manifest.json").read_text("utf-8")).get("version")
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, str) and value else None


def revision(folder: Path) -> str:
    digest = hashlib.sha256()
    for relative, path in sorted(files(folder).items()):
        digest.update(str(relative).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def pending_restart(loaded_revision: str, folder: Path) -> dict[str, str | None] | None:
    marker = folder / MARKER
    try:
        update = json.loads(marker.read_text("utf-8"))
    except (OSError, ValueError, AttributeError):
        return None
    if update.get("to_revision") == loaded_revision:
        marker.unlink(missing_ok=True)
        return None
    return update
