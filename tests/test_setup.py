"""Exercise the firmware's first-run state selection without hardware."""

import subprocess
from pathlib import Path


def test_setup_states(tmp_path):
    executable = tmp_path / "setup-check"
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(Path(__file__).with_name("setup_check.cpp")),
            "-o",
            str(executable),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run([str(executable)], check=True, capture_output=True)
