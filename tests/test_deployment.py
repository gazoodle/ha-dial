import importlib.util
import json
from pathlib import Path


def load(name: str, relative: str):
    path = Path(__file__).parents[1] / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_installer_marks_changed_code_and_restart_check_clears_loaded_version(tmp_path):
    deploy = load("ha_dial_deploy", "tools/deploy.py")
    deployment = load(
        "ha_dial_deployment", "custom_components/ha_dial/deployment.py"
    )
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    (source / "manifest.json").write_text('{"version":"0.1.0"}')
    (source / "code.py").write_text("first")

    assert deploy.install(source, destination) == "installed"
    loaded_revision = deployment.revision(destination)
    assert deployment.pending_restart(loaded_revision, destination) is None

    (source / "code.py").write_text("second")
    assert deploy.install(source, destination) == "updated"
    update = deployment.pending_restart(loaded_revision, destination)
    assert update is not None
    assert update["to_version"] == "0.1.0"
    assert json.loads((destination / deploy.MARKER).read_text())["to_revision"]
