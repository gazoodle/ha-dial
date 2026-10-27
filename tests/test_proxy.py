import json
import os
import subprocess
from pathlib import Path


def test_dial_proxy_has_its_own_port(tmp_path):
    (tmp_path / "fake_git_host.py").write_text(
        "import json,sys\nprint(json.dumps(sys.argv[1:]))\n"
    )
    env = {**os.environ, "FAKE_GIT_HOST_SOURCE": str(tmp_path)}
    env.pop("HA_DIAL_GIT_PORT", None)
    launcher = Path(__file__).resolve().parents[1] / "tools/serve"
    for override, expected in ((None, "9421"), ("19421", "19421")):
        if override:
            env["HA_DIAL_GIT_PORT"] = override
        result = subprocess.run(
            [str(launcher)], env=env, text=True, capture_output=True, check=True
        )
        args = json.loads(result.stdout)
        assert args[args.index("--port") + 1] == expected
        assert args[args.index("--after-snapshot") + 2].endswith("tools/deploy.py")
