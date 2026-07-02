from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

TRIVY_IMAGE = (
    "aquasec/trivy@sha256:"
    "665030f4d33a82c1e8d9d5e0453365842236723c1ee5cc3becca698268e66a56"
)  # 0.58.2


class TrivyNotFoundError(RuntimeError):
    pass


DEFAULT_SCANNERS = "vuln,secret,misconfig"
DEFAULT_SEVERITY = "HIGH,CRITICAL"


def _trivy_bin() -> str | None:
    return shutil.which("trivy")


def build_default_fs_args(
    path: Path,
    *,
    severity: str = DEFAULT_SEVERITY,
    scanners: str = DEFAULT_SCANNERS,
    fmt: str = "table",
    output: Path | None = None,
    ignore_file: Path | None = None,
    exit_code: int | None = 1,
) -> list[str]:
    args = [
        "fs",
        str(path),
        "--severity",
        severity,
        "--scanners",
        scanners,
        "--format",
        fmt,
    ]
    if output is not None:
        args.extend(["--output", str(output)])
    if ignore_file is not None and ignore_file.exists():
        args.extend(["--ignorefile", str(ignore_file)])
    if exit_code is not None:
        args.extend(["--exit-code", str(exit_code)])
    return args


def _rel_to_workdir(path: Path, workdir: Path) -> str:
    try:
        rel = path.resolve().relative_to(workdir.resolve())
        return "." if rel == Path(".") else str(rel)
    except ValueError:
        return str(path)


def _dockerize_args(args: list[str], *, workdir: Path) -> list[str]:
    """Rewrite host paths to container-relative paths under ``/work``."""
    wd = workdir.resolve()
    out: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "fs" and i + 1 < len(args):
            out.extend(["fs", _rel_to_workdir(Path(args[i + 1]), wd)])
            i += 2
            continue
        if arg in ("--ignorefile", "--output") and i + 1 < len(args):
            out.extend([arg, _rel_to_workdir(Path(args[i + 1]), wd)])
            i += 2
            continue
        out.append(arg)
        i += 1
    return out


def _run_docker_trivy(trivy_args: list[str], *, workdir: Path) -> int:
    if not shutil.which("docker"):
        raise TrivyNotFoundError(
            "trivy not on PATH and docker unavailable. Install trivy or docker."
        )
    cwd = workdir.resolve()
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{cwd}:/work",
        "-w",
        "/work",
        TRIVY_IMAGE,
        *_dockerize_args(trivy_args, workdir=cwd),
    ]
    return subprocess.run(cmd, check=False).returncode  # nosec B603


def run_trivy(
    trivy_args: list[str] | None = None,
    *,
    path: Path | str = ".",
    severity: str = DEFAULT_SEVERITY,
    scanners: str = DEFAULT_SCANNERS,
    fmt: str = "table",
    output: Path | None = None,
    ignore_file: Path | None = None,
    exit_code: int | None = 1,
    use_docker: bool = False,
) -> int:
    """Run ``trivy``; passthrough args when provided, else default repo fs scan."""
    root = Path(path).resolve()
    ignore = ignore_file or root / ".trivyignore"
    if trivy_args:
        args = trivy_args
    else:
        args = build_default_fs_args(
            root,
            severity=severity,
            scanners=scanners,
            fmt=fmt,
            output=output,
            ignore_file=ignore,
            exit_code=exit_code,
        )

    if use_docker or _trivy_bin() is None:
        return _run_docker_trivy(args, workdir=root)

    return subprocess.run([_trivy_bin(), *args], check=False).returncode  # nosec B603
