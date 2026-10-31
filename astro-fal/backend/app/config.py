from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROVIDER_DEFAULTS = {
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    # Gemini's OpenAI-compatible endpoint. Verify the current Flash model id before deploying.
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["openai", "gemini", "fake"] = "fake"
    llm_api_key: str = ""
    llm_base_url: str | None = None
    vision_model: str | None = None
    text_model: str | None = None
    llm_timeout_s: float = 45.0

    swisseph_path: str | None = None  # None -> built-in Moshier ephemeris
    default_tz: str = "Europe/Istanbul"

    def resolved(self) -> tuple[str, str, str]:
        """(base_url, vision_model, text_model)"""
        base, model = _PROVIDER_DEFAULTS.get(self.llm_provider, ("", "fake-llm"))
        return self.llm_base_url or base, self.vision_model or model, self.text_model or model


@lru_cache
def get_settings() -> Settings:
    return Settings()
