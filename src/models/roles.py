from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, auto
import inspect
from types import UnionType
from typing import Union, get_args, get_origin
from utils.log import get_logger

LOGGER = get_logger(__file__)


class Role(StrEnum):
    CALLER = auto()
    EVAL = auto()
    FAILURE = auto()


@dataclass(frozen=True, slots=True)
class RegisteredFunc:
    name: str
    role: Role
    func: Callable[..., object]


@dataclass(frozen=True, slots=True)
class RoleContract:
    arity: int
    return_types: frozenset[type] | None = None  # None = any return ok


ROLE_CONTRACTS: dict[Role, RoleContract] = {
    Role.CALLER: RoleContract(arity=1),
    Role.EVAL: RoleContract(arity=2, return_types=frozenset({bool})),
    Role.FAILURE: RoleContract(arity=2),
}


def _accepts_exception(annotation: object) -> bool:
    if annotation is inspect.Parameter.empty:
        return True
    if annotation is Exception or annotation is BaseException:
        return True
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return any(t in (Exception, BaseException) for t in get_args(annotation))
    return False


def _return_type_ok(annotation: object, allowed: frozenset[type]) -> bool:
    if annotation is inspect.Parameter.empty:
        return True
    if annotation in allowed:
        return True
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return all(t in allowed or t is type(None) for t in get_args(annotation))
    return False


def validate_signature(func: Callable[..., object], role: Role) -> None:
    contract = ROLE_CONTRACTS[role]
    target = inspect.unwrap(func)
    sig = inspect.signature(target)
    params = [
        p
        for p in sig.parameters.values()
        if p.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]

    if len(params) != contract.arity:
        err = (
            f"{target.__qualname__} registered as {role}: "
            f"expected {contract.arity} positional param(s), got {len(params)} ({sig})"
        )
        LOGGER.error(err)
        raise TypeError(err)

    if role is Role.FAILURE and not _accepts_exception(params[1].annotation):
        err = (
            f"{target.__qualname__} failure handler: "
            f"second param must accept Exception, got {params[1].annotation!r}"
        )
        LOGGER.error(err)
        raise TypeError(err)

    if contract.return_types and not _return_type_ok(
        sig.return_annotation, contract.return_types
    ):
        err = (
            f"{target.__qualname__} registered as {role}: "
            f"return must be {set(contract.return_types)}, got {sig.return_annotation!r}"
        )
        LOGGER.error(err)
        raise TypeError(err)
