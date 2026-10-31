import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("script", ["card_check.mjs", "panel_check.mjs"])
def test_browser_code_lifecycle(script):
    result = subprocess.run(
        ["node", f"tests/{script}"],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
