from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"),
    )
    openai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_BASE_URL", "openai_base_url"),
    )

    api_key: str = Field(
        default="",
        validation_alias=AliasChoices("NEUGATE_API_KEY", "api_key"),
        description="Service-to-service API key. When set, required on /v1/* endpoints.",
    )

    llm_timeout_seconds: float = Field(default=8.0, validation_alias="NEUGATE_LLM_TIMEOUT_SECONDS")
    llm_max_tokens: int = Field(default=128, validation_alias="NEUGATE_LLM_MAX_TOKENS")

    config_dir: Path = Field(
        default=Path("config/projects"),
        validation_alias=AliasChoices("NEUGATE_CONFIG_DIR", "config_dir"),
    )
    schema_path: Path = Field(
        default=Path("config/schema/neugate-schema.json"),
        validation_alias=AliasChoices("NEUGATE_SCHEMA_PATH", "schema_path"),
    )

    test_runner_max_cases: int = Field(
        default=100,
        validation_alias=AliasChoices("NEUGATE_TEST_RUNNER_MAX_CASES", "test_runner_max_cases"),
        ge=1,
        le=500,
    )
    test_runner_concurrency: int = Field(
        default=10,
        validation_alias=AliasChoices("NEUGATE_TEST_RUNNER_CONCURRENCY", "test_runner_concurrency"),
        ge=1,
        le=50,
    )

    host: str = Field(default="0.0.0.0", validation_alias="NEUGATE_HOST")
    port: int = Field(default=8080, validation_alias="NEUGATE_PORT")
    log_level: str = Field(default="info", validation_alias="NEUGATE_LOG_LEVEL")

    agentic_enabled: bool = Field(default=True, validation_alias="NEUGATE_AGENTIC_ENABLED")
    agentic_index_path: Path = Field(
        default=Path("config/agentic/neugate_agentic.index"),
        validation_alias="NEUGATE_AGENTIC_INDEX_PATH",
    )
    agentic_meta_path: Path = Field(
        default=Path("config/agentic/neugate_agentic.meta.json"),
        validation_alias="NEUGATE_AGENTIC_META_PATH",
    )
    agentic_threshold: float = Field(default=0.82, validation_alias="NEUGATE_AGENTIC_THRESHOLD")
    agentic_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        validation_alias="NEUGATE_AGENTIC_MODEL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
