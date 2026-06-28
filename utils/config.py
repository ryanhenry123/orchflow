from pydantic import Field, AliasChoices, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from utils.enums import LogLevel


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    LOGLEVEL: LogLevel = Field(
        default=LogLevel.INFO, validation_alias=AliasChoices("LOGLEVEL", "LOG_LEVEL")
    )
    MODELPROVIDERKEY: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("MODELPROVIDERKEY", "OPENAI_API_KEY")
    )
