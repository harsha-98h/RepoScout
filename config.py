"""
Configuration for RepoScout Agent.

Settings are loaded from environment variables and the ``.env`` file.
Required secrets (``OPENAI_API_KEY``) raise a clear error on startup if
they are missing, instead of silently passing ``None`` into the API client.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Try to use pydantic-settings for strict, typed configuration.
# If pydantic-settings is not installed fall back to plain os.getenv so the
# application remains usable without that optional dependency.
# ---------------------------------------------------------------------------
try:
    from pydantic import field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class _Settings(BaseSettings):
        # Required secrets – missing values raise a clear ValidationError
        openai_api_key: str
        github_token: str = ""

        # Optional tweaks
        agent_name: str = "RepoScout"
        debug: bool = False
        openai_model: str = "gpt-4o-mini"
        github_api_base: str = "https://api.github.com"
        max_iterations: int = 10
        temperature: float = 0.7
        default_results: int = 5
        min_stars: int = 100

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",  # Ignore extra keys in the user's .env file
        )

        @field_validator("temperature")
        @classmethod
        def _validate_temperature(cls, v: float) -> float:
            if not 0.0 <= v <= 2.0:
                raise ValueError("temperature must be between 0.0 and 2.0")
            return v

        @field_validator("max_iterations")
        @classmethod
        def _validate_max_iterations(cls, v: int) -> int:
            if v < 1:
                raise ValueError("max_iterations must be at least 1")
            return v

    _settings = _Settings()  # type: ignore[call-arg]

    OPENAI_API_KEY: str = _settings.openai_api_key
    GITHUB_TOKEN: str = _settings.github_token
    AGENT_NAME: str = _settings.agent_name
    DEBUG: bool = _settings.debug
    OPENAI_MODEL: str = _settings.openai_model
    GITHUB_API_BASE: str = _settings.github_api_base
    MAX_ITERATIONS: int = _settings.max_iterations
    TEMPERATURE: float = _settings.temperature
    DEFAULT_RESULTS: int = _settings.default_results
    MIN_STARS: int = _settings.min_stars

except ImportError:
    # pydantic-settings not installed – fall back to os.getenv
    import warnings
    warnings.warn(
        "pydantic-settings is not installed. Falling back to os.getenv. "
        "Install it with: pip install pydantic-settings",
        stacklevel=1,
    )

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")  # type: ignore[assignment]
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    AGENT_NAME: str = os.getenv("AGENT_NAME", "RepoScout")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    OPENAI_MODEL: str = "gpt-4o-mini"
    GITHUB_API_BASE: str = "https://api.github.com"
    MAX_ITERATIONS: int = 10
    TEMPERATURE: float = 0.7
    DEFAULT_RESULTS: int = 5
    MIN_STARS: int = 100