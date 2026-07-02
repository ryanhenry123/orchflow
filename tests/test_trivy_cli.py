from unittest.mock import patch

import pytest

from orchflow.cli import main
from orchflow.security.trivy import (
    TRIVY_IMAGE,
    build_default_fs_args,
    run_trivy,
)


def test_build_default_fs_args():
    args = build_default_fs_args(".", fmt="json", exit_code=1)
    assert args[:2] == ["fs", "."]
    assert "--severity" in args
    assert "--exit-code" in args


def test_run_trivy_default_scan():
    with patch("orchflow.security.trivy._trivy_bin", return_value="/usr/bin/trivy"):
        with patch("orchflow.security.trivy.subprocess.run") as run:
            run.return_value.returncode = 0
            code = run_trivy()
    assert code == 0
    cmd = run.call_args.args[0]
    assert cmd[0] == "/usr/bin/trivy"
    assert cmd[1] == "fs"


def test_run_trivy_passthrough():
    with patch("orchflow.security.trivy._trivy_bin", return_value="/usr/bin/trivy"):
        with patch("orchflow.security.trivy.subprocess.run") as run:
            run.return_value.returncode = 0
            run_trivy(["image", "alpine:3.20"])
    cmd = run.call_args.args[0]
    assert cmd == ["/usr/bin/trivy", "image", "alpine:3.20"]


def test_run_trivy_docker_uses_pinned_image():
    with patch("orchflow.security.trivy._trivy_bin", return_value=None):
        with patch(
            "orchflow.security.trivy.shutil.which", return_value="/usr/bin/docker"
        ):
            with patch("orchflow.security.trivy.subprocess.run") as run:
                run.return_value.returncode = 0
                run_trivy(use_docker=True, path="/home/ryanh/orchflow")
    cmd = run.call_args.args[0]
    assert TRIVY_IMAGE in cmd
    assert cmd[0] == "docker"
    joined = " ".join(cmd)
    assert "/home/ryanh/orchflow/.trivyignore" not in joined


def test_dockerize_args_rewrites_paths(tmp_path):
    from orchflow.security.trivy import _dockerize_args

    ignore = tmp_path / ".trivyignore"
    ignore.write_text("# ignore\n")
    args = _dockerize_args(
        ["fs", str(tmp_path), "--ignorefile", str(ignore)],
        workdir=tmp_path,
    )
    assert args == ["fs", ".", "--ignorefile", ".trivyignore"]


def test_cli_trivy_subcommand(capsys):
    with patch("orchflow.security.trivy.run_trivy", return_value=0) as run:
        with pytest.raises(SystemExit) as exc:
            main(["trivy", "--exit-code", "0"])
    assert exc.value.code == 0
    run.assert_called_once()
    assert run.call_args.kwargs["exit_code"] == 0
