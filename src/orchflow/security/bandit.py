from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

DEFAULT_SEVERITY = "low"
DEFAULT_FORMAT = "txt"


class BanditNotFoundError(RuntimeError):
    pass


def _bandit_cmd() -> list[str]:
    if shutil.which("bandit"):
        return ["bandit"]
    return [sys.executable, "-m", "bandit"]


def _bandit_available() -> bool:
    if shutil.which("bandit"):
        return True
    try:
        import bandit  # noqa: F401
    except ImportError:
        return False
    return True


def build_default_args(
    path: Path,
    *,
    config: Path | None = None,
    severity: str = DEFAULT_SEVERITY,
    fmt: str = DEFAULT_FORMAT,
    exit_code: int | None = 1,
) -> list[str]:
    args = ["-r", str(path)]
    if config is not None and config.exists():
        args.extend(["-c", str(config)])
    if severity == "low":
        args.append("-ll")
    elif severity == "medium":
        args.append("-l")
    if fmt != DEFAULT_FORMAT:
        args.extend(["-f", fmt])
    if exit_code == 0:
        args.append("--exit-zero")
    return args


def _default_config() -> Path | None:
    cfg = Path(".github/bandit.yaml")
    return cfg if cfg.exists() else None


def run_bandit(
    bandit_args: list[str] | None = None,
    *,
    path: Path | str = "src/orchflow",
    config: Path | None = None,
    severity: str = DEFAULT_SEVERITY,
    fmt: str = DEFAULT_FORMAT,
    exit_code: int | None = 1,
) -> int:
    """Run ``bandit``; passthrough args when provided, else default repo scan."""
    root = Path(path).resolve()
    cfg = config if config is not None else _default_config()

    if bandit_args:
        args = bandit_args
    else:
        args = build_default_args(
            root,
            config=cfg,
            severity=severity,
            fmt=fmt,
            exit_code=exit_code,
        )

    if not _bandit_available():
        raise BanditNotFoundError(
            "bandit not installed. Run: uv sync --all-groups"
        )

    return subprocess.run([*_bandit_cmd(), *args], check=False).returncode  # nosec B603
