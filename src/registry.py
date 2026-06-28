from collections import Counter
from collections.abc import Callable
from typing import Self
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from yaml import safe_load
from utils.log import get_logger
from src.models.roles import Role
from src.registerfuncs import from_registry, registered_names

LOGGER = get_logger(__file__)


class Context(BaseModel):
    """State to be passed through the DAG."""

    model_config = {"arbitrary_types_allowed": True}
    data: dict[str, object] = Field(default_factory=dict)


# Serializable Steps (YAML / JSON supported)


class StepSpec(BaseModel):
    step_name: str
    caller: str
    eval: str | None = None
    on_failure: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class WorkflowSpec(BaseModel):
    name: str
    steps: list[StepSpec]

    @model_validator(mode="after")
    def unique_step_names(self) -> Self:
        names = [s.step_name for s in self.steps]
        if len(names) != len(set(names)):
            cts = Counter(names)
            err = f"Duplicate step name(s): {','.join(sorted(n for n, ct in cts.items() if ct > 1))}"
            LOGGER.error(err)
            raise ValueError(err)
        return self

    @classmethod
    def load(cls, path: Path) -> Self:
        payload = safe_load(path.read_text())
        if not isinstance(payload, dict):
            err = f"Type mismatch on workflow payload. Expected dict, received: {type(payload)}"
            LOGGER.error(err)
            raise TypeError(err)
        return cls.model_validate(payload)

    def referenced_function_names(self) -> set[str]:
        names: set[str] = set()
        for step in self.steps:
            names.add(step.caller)
            if step.eval:
                names.add(step.eval)
            if step.on_failure:
                names.add(step.on_failure)
        return names


# Runtime Steps


class Step(BaseModel):
    step_name: str
    caller_func: Callable[[Context], object]
    eval_func: Callable[[Context, object], bool] | None = None
    failure_func: Callable[[Context, Exception], object] | None = None
    depends_on: list[str] = Field(default_factory=list)

    @classmethod
    def from_spec(cls, spec: StepSpec) -> Self:
        return cls(
            step_name=spec.step_name,
            caller_func=from_registry(spec.caller, Role.CALLER),
            eval_func=from_registry(spec.eval, Role.EVAL) if spec.eval else None,
            failure_func=(
                from_registry(spec.on_failure, Role.FAILURE)
                if spec.on_failure
                else None
            ),
            depends_on=list(spec.depends_on),
        )


class StepRegistry:
    def __init__(self) -> None:
        self._steps: dict[str, Step] = {}

    def add(self, step: Step) -> None:
        if step.step_name in self._steps:
            err = f"Duplicate step: {step.step_name}."
            LOGGER.error(err)
            raise ValueError(err)
        self._steps[step.step_name] = step

    def add_spec(self, spec: StepSpec) -> None:
        self.add(Step.from_spec(spec))

    def load_workflow(self, spec: WorkflowSpec) -> None:
        # 1) All YAML-referenced functions exist in registerfuncs
        missing = spec.referenced_function_names() - registered_names()
        if missing:
            err = f"Unregistered task(s): {sorted(missing)}"
            LOGGER.error(err)
            raise ValueError(err)
        # 2) Step graph structure is valid, then resolve each step
        known_steps = {s.step_name for s in spec.steps}
        for s in spec.steps:
            missing_deps = set(s.depends_on) - known_steps
            if missing_deps:
                err = f"{s.step_name} depends on unknown steps: {sorted(missing_deps)}"
                LOGGER.error(err)
                raise ValueError(err)
            self.add_spec(s)

    def all(self) -> list[Step]:
        return list(self._steps.values())

    def get(self, name: str) -> Step:
        try:
            return self._steps[name]
        except KeyError:
            err = f"Unknown step: {name}"
            LOGGER.error(err)
            raise KeyError(err) from None
