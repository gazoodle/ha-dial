"""Independent Casa Mia-style versions for HA Dial Server and firmware."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = {
    "integration": (
        "pyproject.toml",
        re.compile(r'(?m)^version = "([^"]+)"$'),
        "CHANGELOG.md",
        ("custom_components/ha_dial", "pyproject.toml"),
    ),
    "firmware": (
        "firmware/version.yaml",
        re.compile(r'(?m)^  firmware_version: "([^"]+)"$'),
        "firmware/CHANGELOG.md",
        (
            "components/ha_dial",
            "firmware/ha-dial.yaml",
            "firmware/ha-dial-connected.yaml",
            "firmware/pointer.h",
            "firmware/version.yaml",
        ),
    ),
}
VERSION_RE = re.compile(r"^(\d{4})\.(1[0-2]|[1-9])\.([1-9]\d*)(?:-b([1-9]\d*))?$")
HEADING_RE = re.compile(r"(?m)^## (\S+)\n")


def parse(version: str) -> tuple[int, int, int, int | None]:
    match = VERSION_RE.fullmatch(version)
    if not match:
        raise ValueError(f"Expected YYYY.M.R or YYYY.M.R-bN, got {version!r}")
    year, month, release, build = match.groups()
    return int(year), int(month), int(release), int(build) if build else None


def next_build(version: str, today: dt.date) -> str:
    year, month, release, build = parse(version)
    if build is not None:
        return f"{year}.{month}.{release}-b{build + 1}"
    if (year, month) == (today.year, today.month):
        return f"{year}.{month}.{release + 1}-b1"
    return f"{today.year}.{today.month}.1-b1"


def current(component: str, root: Path = ROOT) -> str:
    source, pattern, _, _ = COMPONENTS[component]
    match = pattern.search((root / source).read_text())
    if not match:
        raise ValueError(f"No version in {source}")
    version = match.group(1)
    parse(version)
    return version


def head_version(component: str, root: Path) -> str | None:
    source, pattern, _, _ = COMPONENTS[component]
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"HEAD:{source}"],
        check=False,
        capture_output=True,
        text=True,
    )
    match = pattern.search(result.stdout) if result.returncode == 0 else None
    return match.group(1) if match else None


def sync(component: str, root: Path = ROOT) -> str:
    version = current(component, root)
    if component == "integration":
        path = root / "custom_components/ha_dial/manifest.json"
        manifest = json.loads(path.read_text())
        if manifest["version"] != version:
            manifest["version"] = version
            path.write_text(json.dumps(manifest, indent=2) + "\n")
    return version


def write(component: str, version: str, root: Path) -> None:
    source, pattern, _, _ = COMPONENTS[component]
    path = root / source
    path.write_text(
        pattern.sub(
            lambda match: match[0].replace(match[1], version), path.read_text(), count=1
        )
    )
    sync(component, root)


def bump(component: str, root: Path = ROOT, today: dt.date | None = None) -> str:
    version = current(component, root)
    if head_version(component, root) == version:
        version = next_build(version, today or dt.date.today())
        write(component, version, root)
        log = root / COMPONENTS[component][2]
        text = log.read_text()
        first = HEADING_RE.search(text)
        position = first.start() if first else len(text)
        log.write_text(text[:position] + f"## {version}\n\n" + text[position:])
    return sync(component, root)


def release(component: str, root: Path = ROOT, today: dt.date | None = None) -> str:
    year, month, number, build = parse(current(component, root))
    if build is None:
        raise ValueError("Already a release")
    today = today or dt.date.today()
    if (year, month) != (today.year, today.month):
        year, month, number = today.year, today.month, 1
    version = f"{year}.{month}.{number}"
    log = root / COMPONENTS[component][2]
    text = log.read_text()
    headings = list(HEADING_RE.finditer(text))
    if not headings or headings[0][1] != current(component, root):
        raise ValueError("Current version needs a changelog heading")
    end, notes = len(text), []
    for index, heading in enumerate(headings):
        if parse(heading[1])[3] is None:
            end = heading.start()
            break
        next_start = (
            headings[index + 1].start() if index + 1 < len(headings) else len(text)
        )
        notes.append(text[heading.end() : next_start].strip())
    log.write_text(
        text[: headings[0].start()]
        + f"## {version}\n\n"
        + "\n\n".join(filter(None, notes))
        + "\n\n"
        + text[end:]
    )
    write(component, version, root)
    return version


def check(component: str, root: Path = ROOT) -> str:
    version = current(component, root)
    heading = HEADING_RE.search((root / COMPONENTS[component][2]).read_text())
    if not heading or heading[1] != version:
        raise ValueError(f"{component} changelog needs a {version} heading")
    if component == "integration":
        manifest = json.loads(
            (root / "custom_components/ha_dial/manifest.json").read_text()
        )
        if manifest["version"] != version:
            raise ValueError("Run tools/versioning.py sync integration")
    if head_version(component, root) == version:
        paths = COMPONENTS[component][3]
        for command in (
            ["diff", "--name-only", "HEAD", "--", *paths],
            ["ls-files", "--others", "--exclude-standard", "--", *paths],
        ):
            changed = subprocess.run(
                ["git", "-C", str(root), *command],
                check=True,
                capture_output=True,
                text=True,
            )
            if changed.stdout.strip():
                raise ValueError(
                    f"{component} changed without a version bump; run tools/versioning.py bump {component}"
                )
    return version


def main() -> int:
    actions = {"bump": bump, "release": release, "sync": sync, "check": check}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=actions)
    parser.add_argument("component", choices=COMPONENTS)
    args = parser.parse_args()
    try:
        version = actions[args.action](args.component)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    sys.stdout.write(f"{args.component} {version}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
