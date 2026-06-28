from pathlib import Path
from typing import Self
from pydantic import BaseModel, Field
from yaml import safe_load
from utils.log import get_logger

LOGGER = get_logger(__file__)


class PromptTemplate(BaseModel):
    name: str
    version: str = "1"
    system: str
    user_input: str
    variables: list[str] = Field(default_factory=list)
    description: str = ""


class PromptConfig(BaseModel):
    prompt: PromptTemplate
    model: str
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = None

    @classmethod
    def load_prompt_config(cls, path: Path) -> Self:
        return cls.model_validate(safe_load(path.read_text()))


class PromptRequest(BaseModel):
    prompt_name: str
    system_input: str
    variables: dict[str, str] = Field(default_factory=dict)

    def render_prompt(self, config: PromptConfig) -> tuple[str, str]:
        variables = {"system_input": self.system_input, **self.variables}
        missing = set(config.prompt.variables) - variables.keys
        if missing:
            err = f"Missing prompt variables: {missing}."
            LOGGER.error(err)
            raise ValueError(err)
        user = config.prompt.user_input.format(**variables)
        return config.prompt.system, user
