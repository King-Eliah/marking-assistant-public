"""Application configuration.

Every value here maps to a variable in `.env.example`, which is generated from
spec.md Appendix A. Nothing is read from the environment outside this module.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration. See docs/spec.md Appendix A."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- core
    app_env: Literal["development", "staging", "production"] = "development"
    secret_key_id: str = "local-dev-only"
    jwt_private_key_path: str = "/run/secrets/jwt_rs256.pem"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 604800

    # 5433 on the host — see the port comment in docker-compose.yml.
    database_url: str = "postgresql+psycopg://marking:marking@localhost:5433/marking"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "marking-assistant"
    s3_region: str = "us-east-1"

    # --- pipeline versions (pinned; changing any invalidates caches)
    pipeline_version: str = "2.3.1"
    rule_engine_version: str = "4.2.0"
    embedding_model: str = "bge-m3@1.0"
    reranker_model: str = "bge-reranker-v2-m3@1.0"
    nli_model: str = "deberta-v3-base-mnli@1.0"
    prompt_version: str = "v3"

    # --- providers
    ocr_primary: str = "google_vision"
    ocr_secondary: str = "azure_read"
    ocr_arbiter: str = "gemini_flash_lite"
    entailment_provider: str = "gemini_flash_lite"
    provider_timeout_seconds: int = 20
    provider_max_retries: int = 3
    circuit_breaker_threshold: int = 5

    # --- thresholds (defaults; per-tenant overrides bounded by these)
    image_quality_reject: float = 0.50
    image_quality_warn: float = 0.70
    ocr_tier2_threshold: float = 0.88
    ocr_tier2_max_lines_per_page: int = 30
    entail_confidence_floor: float = 0.65
    auto_suggest_threshold: float = 0.85
    manual_only_threshold: float = 0.70
    platform_min_auto_suggest: float = 0.80

    # --- limits
    max_upload_bytes: int = 15_728_640
    max_batch_files: int = 500
    max_image_pixels: int = 80_000_000
    work_long_edge: int = 2400
    tenant_monthly_ai_cap_usd: int = 100
    tenant_max_inflight_jobs: int = 50

    # --- retention
    image_retention_days: int = 180
    marks_retention_days: int = 2555


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
