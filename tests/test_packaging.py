import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


@pytest.fixture(scope="module")
def wheel_path() -> Path:
    subprocess.run(
        ["uv", "build"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = sorted(DIST.glob("orchflow-*.whl"))
    assert wheels, "uv build did not produce a wheel"
    return wheels[-1]


def test_core_import_without_aws_extra(wheel_path: Path, tmp_path: Path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    python = venv / "bin" / "python"
    subprocess.run([pip, "install", str(wheel_path)], check=True, capture_output=True)
    code = subprocess.run(
        [
            python,
            "-c",
            "from orchflow import Context, markdown_sections, __version__; "
            "assert __version__; "
            "assert markdown_sections('## Summary')",
        ],
        capture_output=True,
        text=True,
    ).returncode
    assert code == 0


def test_cli_eval_without_aws_extra(wheel_path: Path, tmp_path: Path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    orchflow = venv / "bin" / "orchflow"
    fixture = ROOT / "tests" / "fixtures" / "simple" / "good.md"
    subprocess.run([pip, "install", str(wheel_path)], check=True, capture_output=True)
    proc = subprocess.run(
        [
            orchflow,
            "eval",
            str(fixture),
            "--panel",
            "orchflow.examples.simple_evals:SIMPLE_EVALS",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "good.md: ok" in proc.stdout
