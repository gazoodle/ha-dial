"""Calendar versions bump independently and stay in sync with deployment metadata."""

import datetime as dt
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


def load_versioning():
    path = Path(__file__).resolve().parents[1] / "tools/versioning.py"
    spec = importlib.util.spec_from_file_location("dial_versioning", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def commit(root):
    subprocess.run(
        ["git", "-C", str(root), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Version test",
            "-c",
            "user.email=version@example.invalid",
            "commit",
            "-qm",
            "Version fixture",
        ],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def versions(tmp_path):
    source = {
        "pyproject.toml": 'version = "2026.10.1-b3"\n',
        "custom_components/ha_dial/manifest.json": json.dumps(
            {"version": "2026.10.1-b3"}, indent=2
        )
        + "\n",
        "custom_components/ha_dial/demo.py": "# Initial fixture\n",
        "CHANGELOG.md": "# Server\n\n## 2026.10.1-b3\n\n- Server change.\n",
        "firmware/version.yaml": 'substitutions:\n  firmware_version: "2026.10.2-b7"\n',
        "firmware/CHANGELOG.md": "# Firmware\n\n## 2026.10.2-b7\n\n- Firmware change.\n\n## 2026.10.1\n\n- Previous release.\n",
        "components/ha_dial/demo.h": "#pragma once\n",
    }
    for relative, text in source.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run(
        ["git", "init", "-q", str(tmp_path)], check=True, capture_output=True
    )
    commit(tmp_path)
    return load_versioning(), tmp_path


@pytest.mark.parametrize(
    ("current", "today", "expected"),
    [
        ("2026.10.1-b3", dt.date(2026, 10, 29), "2026.10.1-b4"),
        ("2026.10.1-b3", dt.date(2026, 11, 1), "2026.10.1-b4"),
        ("2026.10.1", dt.date(2026, 10, 29), "2026.10.2-b1"),
        ("2026.10.1", dt.date(2027, 1, 1), "2027.1.1-b1"),
    ],
)
def test_casa_mia_bump_rules(current, today, expected):
    assert load_versioning().next_build(current, today) == expected


@pytest.mark.parametrize(
    "invalid", ["0.4.0", "2026.01.1-b1", "2026.13.1-b1", "2026.10.1-b0", "2026.10.0-b1"]
)
def test_invalid_calendar_versions_are_rejected(invalid):
    with pytest.raises(ValueError, match="Expected YYYY.M.R"):
        load_versioning().parse(invalid)


@pytest.mark.parametrize("component", ["firmware", "integration"])
def test_bump_is_independent_and_once_per_uncommitted_build(versions, component):
    tool, root = versions
    other = "firmware" if component == "integration" else "integration"
    untouched = tool.current(other, root)
    first = tool.bump(component, root, dt.date(2026, 10, 29))
    assert first != tool.head_version(component, root)
    assert tool.bump(component, root, dt.date(2026, 10, 29)) == first
    assert tool.check(component, root) == first
    assert tool.current(other, root) == untouched
    log = (root / tool.COMPONENTS[component][2]).read_text()
    assert log.count(f"## {first}\n") == 1
    commit(root)
    assert tool.bump(component, root, dt.date(2026, 10, 29)) != first


@pytest.mark.parametrize("untracked", [False, True])
@pytest.mark.parametrize("component", ["integration", "firmware"])
def test_runtime_change_without_bump_is_rejected(versions, untracked, component):
    tool, root = versions
    directory, suffix = (
        ("custom_components/ha_dial", ".py")
        if component == "integration"
        else ("components/ha_dial", ".h")
    )
    path = root / directory / (("new" if untracked else "demo") + suffix)
    path.write_text("# Changed runtime fixture\n")
    with pytest.raises(ValueError, match="changed without a version bump"):
        tool.check(component, root)
    other = "firmware" if component == "integration" else "integration"
    assert tool.check(other, root) == tool.current(other, root)


def test_manifest_sync_and_missing_changelog_are_checked(versions):
    tool, root = versions
    manifest = root / "custom_components/ha_dial/manifest.json"
    manifest.write_text('{"version":"old"}')
    with pytest.raises(ValueError, match="sync integration"):
        tool.check("integration", root)
    tool.sync("integration", root)
    assert json.loads(manifest.read_text())["version"] == tool.current(
        "integration", root
    )
    assert tool.check("integration", root) == "2026.10.1-b3"
    (root / "CHANGELOG.md").write_text("# No notes\n")
    with pytest.raises(ValueError, match="changelog"):
        tool.check("integration", root)


@pytest.mark.parametrize(
    ("today", "expected"),
    [(dt.date(2026, 10, 29), "2026.10.2"), (dt.date(2026, 11, 1), "2026.11.1")],
)
def test_release_uses_current_month_and_merges_build_notes(versions, today, expected):
    tool, root = versions
    assert tool.bump("firmware", root, dt.date(2026, 11, 1)) == "2026.10.2-b8"
    log = root / "firmware/CHANGELOG.md"
    log.write_text(
        log.read_text().replace(
            "## 2026.10.2-b8\n", "## 2026.10.2-b8\n\n- Latest change.\n"
        )
    )
    assert tool.release("firmware", root, today) == expected
    assert (
        "- Latest change." in log.read_text()
        and "- Firmware change." in log.read_text()
    )
    assert "-b" not in log.read_text()
    assert "## 2026.10.1\n" in log.read_text()
    assert tool.current("integration", root) == "2026.10.1-b3"
    with pytest.raises(ValueError, match="Already a release"):
        tool.release("firmware", root)


def test_checkout_versions_are_consistent():
    tool = load_versioning()
    for component in tool.COMPONENTS:
        tool.check(component)
