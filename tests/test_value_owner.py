import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_dial_owns_a_value_until_ha_agrees(tmp_path):
    executable = tmp_path / "value-owner-check"
    subprocess.run(
        ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-UNDEBUG", "-I", str(ROOT / "components/ha_dial"), str(ROOT / "tests/value_owner_check.cpp"), "-o", str(executable)],
        check=True,
        capture_output=True,
    )
    assert subprocess.run([str(executable)], check=True, capture_output=True, text=True).stdout.strip() == "value owner passed"
