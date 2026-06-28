from collections.abc import Callable

from src.models.roles import RegisteredFunc, Role, validate_signature
from utils.log import get_logger

LOGGER = get_logger(__file__)
REGISTRY: dict[str, RegisteredFunc] = {}


def register(name: str, role: Role):
    if not name or not name.strip():
        err = "Task name cannot be empty."
        LOGGER.error(err)
        raise ValueError(err)

    def decorator(func):
        if name in REGISTRY:
            err = f"Duplicate naming error: {name}"
            LOGGER.error(err)
            raise ValueError(err)
        validate_signature(func, role)
        REGISTRY[name] = RegisteredFunc(name=name, role=role, func=func)
        return func

    return decorator


def from_registry(name: str, role: Role) -> Callable[..., object]:
    entry = REGISTRY.get(name)
    if entry is None:
        err = f"Unknown task: {name}."
        LOGGER.error(err)
        raise KeyError(err)
    if entry.role is not role:
        err = f"Task {name!r} is {entry.role}, expected {role}"
        LOGGER.error(err)
        raise TypeError(err)
    return entry.func


def registered_names() -> frozenset[str]:
    return frozenset(REGISTRY)
