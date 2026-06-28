import pytest

from src.models.roles import Role
from src.registerfuncs import REGISTRY, from_registry, register, registered_names
from src.registry import Context


def test_register_and_lookup():
    def task(ctx: Context) -> str:
        return "ok"

    registered = register("task", Role.CALLER)(task)
    assert registered is task
    assert from_registry("task", Role.CALLER) is task
    assert "task" in registered_names()


@pytest.mark.parametrize("role", list(Role))
def test_registered_names_tracks_each_role(role: Role):
    def fn(ctx: Context, result: object | None = None, exc: Exception | None = None):
        return True

    if role is Role.CALLER:

        def fn(ctx: Context) -> bool:  # noqa: F811
            return True

        register("task", role)(fn)
    elif role is Role.EVAL:

        def fn(ctx: Context, result: object) -> bool:  # noqa: F811
            return True

        register("task", role)(fn)
    else:

        def fn(ctx: Context, exc: Exception) -> None:  # noqa: F811
            pass

        register("task", role)(fn)

    assert registered_names() == frozenset({"task"})


def test_duplicate_name_raises():
    def task(ctx: Context) -> None:
        pass

    register("task", Role.CALLER)(task)
    with pytest.raises(ValueError, match="Duplicate naming error"):
        register("task", Role.CALLER)(task)
    assert len(REGISTRY) == 1


@pytest.mark.parametrize("name", ["", "   ", None])
def test_empty_name_raises(name):
    def task(ctx: Context) -> None:
        pass

    with pytest.raises(ValueError, match="Task name cannot be empty"):
        register(name, Role.CALLER)(task)
    assert REGISTRY == {}


def test_from_registry_unknown_raises():
    with pytest.raises(KeyError, match="Unknown task: missing"):
        from_registry("missing", Role.CALLER)


@pytest.mark.parametrize(
    ("registered_role", "requested_role"),
    [
        (Role.CALLER, Role.EVAL),
        (Role.CALLER, Role.FAILURE),
        (Role.EVAL, Role.CALLER),
        (Role.FAILURE, Role.CALLER),
    ],
)
def test_from_registry_wrong_role_raises(registered_role, requested_role):
    if registered_role is Role.CALLER:

        def fn(ctx: Context) -> None:
            pass

    elif registered_role is Role.EVAL:

        def fn(ctx: Context, result: object) -> bool:
            return True

    else:

        def fn(ctx: Context, exc: Exception) -> None:
            pass

    register("task", registered_role)(fn)
    with pytest.raises(TypeError, match="expected"):
        from_registry("task", requested_role)


@pytest.mark.parametrize(
    ("role", "bad"),
    [
        (Role.CALLER, lambda: "x"),
        (Role.EVAL, lambda ctx: True),
        (Role.FAILURE, lambda ctx: None),
    ],
)
def test_register_rejects_invalid_signatures(role, bad):
    with pytest.raises(TypeError):
        register("bad", role)(bad)


def test_register_preserves_function_identity():
    def task(ctx: Context) -> int:
        return 42

    assert register("task", Role.CALLER)(task) is task
    assert from_registry("task", Role.CALLER)(Context()) == 42
