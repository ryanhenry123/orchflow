from logging import basicConfig, getLogger, Logger, WARNING
from sys import stderr
from utils.config import EnvConfig
from utils.enums import LogLevel

_configured = False


def configure_logging(level: LogLevel | None = None) -> None:
    global _configured
    if _configured:
        return
    resolved = level or EnvConfig().LOGLEVEL
    basicConfig(
        level=resolved.to_logging_level(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=stderr,
        force=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> Logger:
    if not _configured:
        configure_logging()
    return getLogger(name or "orchflow")
