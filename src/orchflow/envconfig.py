from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ORCHFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    visible_turns: bool = False
    print_last_draft: bool = False


@lru_cache
def get_settings() -> EnvConfig:
    return EnvConfig()
