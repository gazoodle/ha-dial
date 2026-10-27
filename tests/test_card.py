import subprocess
from pathlib import Path


def test_editor_and_card_lifecycle():
    result = subprocess.run(
        ["node", "tests/card_check.mjs"],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
