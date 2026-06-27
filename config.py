"""
config.py — load all settings from environment; never hardcode secret values.
Call get_settings() everywhere (cached).

Keys default to "" so the foundation builds/imports keyless. Each API client should
raise a clear error only when actually called with an empty key. Fill .env when you
wire real calls (with credits).
"""
from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings  # pydantic v2 — separate package


class Settings(BaseSettings):
    # ── Anthropic ──────────────────────────────────────────────────────
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    grower_model: str = Field("claude-opus-4-8", env="GROWER_MODEL")
    checker_model: str = Field("claude-haiku-4-5", env="CHECKER_MODEL")

    # ── Voyage ─────────────────────────────────────────────────────────
    voyage_api_key: str = Field("", env="VOYAGE_API_KEY")
    voyage_model: str = Field("voyage-3", env="VOYAGE_MODEL")
    voyage_dim: int = Field(1024, env="VOYAGE_DIM")

    # ── MongoDB Atlas ──────────────────────────────────────────────────
    mongodb_uri: str = Field("", env="MONGODB_URI")
    atlas_db: str = Field("bonsai", env="ATLAS_DB")
    atlas_collection: str = Field("failures", env="ATLAS_COLLECTION")
    atlas_vector_index: str = Field("failvec", env="ATLAS_VECTOR_INDEX")

    # ── Gemini AUT ─────────────────────────────────────────────────────
    gemini_api_key: str = Field("", env="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-3.5-pro", env="GEMINI_MODEL")  # AUT model id
    mock_aut: bool = Field(True, env="MOCK_AUT")  # 1 = deterministic offline AUT (no Gemini call)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings()
