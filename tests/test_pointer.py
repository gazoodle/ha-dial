"""Compile and exercise the firmware's platform-independent pointer geometry."""

import subprocess
from pathlib import Path


def test_pointer_geometry_on_host(tmp_path):
    source = Path(__file__).with_name("pointer_check.cpp")
    executable = tmp_path / "pointer-check"
    subprocess.run(
        ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(executable)],
        check=True,
        capture_output=True,
    )
    subprocess.run([str(executable)], check=True, capture_output=True)
