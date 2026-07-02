from unittest.mock import patch

import pytest

from orchflow.cli import main
from orchflow.security.bandit import build_default_args, run_bandit


def test_build_default_args():
    args = build_default_args("src/orchflow", exit_code=1)
    assert args[:2] == ["-r", "src/orchflow"]
    assert "-ll" in args
    assert "--exit-zero" not in args


def test_build_default_args_exit_zero():
    args = build_default_args("src/orchflow", exit_code=0)
    assert "--exit-zero" in args


def test_run_bandit_default_scan():
    with patch("orchflow.security.bandit._bandit_available", return_value=True):
        with patch("orchflow.security.bandit.subprocess.run") as run:
            run.return_value.returncode = 0
            code = run_bandit()
    assert code == 0
    cmd = run.call_args.args[0]
    assert cmd[-2] == "-r" or "-r" in cmd
    assert "bandit" in cmd[0] or cmd[1:3] == ["-m", "bandit"]


def test_run_bandit_passthrough():
    with patch("orchflow.security.bandit._bandit_available", return_value=True):
        with patch("orchflow.security.bandit.subprocess.run") as run:
            run.return_value.returncode = 0
            run_bandit(["-r", "src", "-f", "json"])
    cmd = run.call_args.args[0]
    assert "-r" in cmd
    assert "json" in cmd


def test_cli_bandit_subcommand():
    with patch("orchflow.security.bandit.run_bandit", return_value=0) as run:
        with pytest.raises(SystemExit) as exc:
            main(["bandit", "--exit-code", "0"])
    assert exc.value.code == 0
    run.assert_called_once()
    assert run.call_args.kwargs["exit_code"] == 0
