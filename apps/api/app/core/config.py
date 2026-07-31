"""Application configuration.

Every value here maps to a variable in `.env.example`, which is generated from
spec.md Appendix A. Nothing is read from the environment outside this module.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

#: apps/api/app/core/config.py -> apps/api/app/core -> ... -> repository root
_REPO_ROOT = Path(__file__).resolve().parents[4]

#: Both locations are searched, later entries winning.
#:
#: Resolved from this file rather than written as a bare `".env"`, which
#: pydantic-settings resolves against the *working directory*. Everything here
#: runs from `apps/api` while `.env` lives at the repository root, so the bare
#: form silently found nothing and every setting quietly used its default —
#: including `DATABASE_URL`, which is how an unnoticed misconfiguration could
#: have pointed the application at the wrong role.
_ENV_FILES = (_REPO_ROOT / ".env", _REPO_ROOT / "apps" / "api" / ".env")


class Settings(BaseSettings):
    """Environment configuration. See docs/spec.md Appendix A."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- core
    app_env: Literal["development", "staging", "production"] = "development"
    secret_key_id: str = "local-dev-only"
    jwt_private_key_path: str = "/run/secrets/jwt_rs256.pem"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 604800

    #: Comma-separated Fernet keys, newest first. Encrypts student index
    #: numbers at rest. Multiple keys allow rotation: new writes use the first,
    #: existing ciphertexts stay readable under the rest.
    #:
    #: Empty is tolerated only in development, where an ephemeral key is
    #: generated. Anywhere else the application refuses to start, because a
    #: lost key means marks survive with no way to tell whose they are.
    identity_encryption_keys: str = ""

    # `marking_app`, never the migration owner. The owner is a superuser in dev
    # and superusers bypass RLS entirely, so pointing the application at it
    # silently disables tenant isolation while every query still succeeds.
    # `assert_rls_applies()` enforces this at startup rather than trusting it.
    # 5433 on the host — see the port comment in docker-compose.yml.
    database_url: str = "postgresql+psycopg://marking_app:marking_app@localhost:5433/marking"

    #: Migrations only. Owns the schema and creates `marking_app`, so it needs
    #: privileges the application must never hold. Kept separate precisely so
    #: the runtime credential cannot quietly acquire them.
    migration_database_url: str = "postgresql+psycopg://marking:marking@localhost:5433/marking"
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

    #: Origins allowed to call this API from a browser, comma separated.
    #:
    #: Explicit origins, never `*`. The clients send credentials so the browser
    #: refuses a wildcard outright — and a wildcard would in any case let any
    #: site make authenticated calls on a signed-in user's behalf.
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- provider credentials
    #
    # Never literals in code or in a committed file. `.env` is gitignored;
    # anything deployed reads these from a secret manager. A key in git history
    # is a key that has to be rotated, and rotating a Google service account
    # means every worker restarts.
    #
    #: Absolute path to the service-account JSON downloaded from Google Cloud.
    #: The path, not the contents — the file itself must stay outside the repo.
    google_application_credentials: str = ""
    #: From https://aistudio.google.com/apikey
    gemini_api_key: str = ""

    @property
    def has_ocr_credentials(self) -> bool:
        """Whether a real OCR call is possible.

        Checked at the point of use rather than at startup: the whole booklet,
        capture and evaluation path works without any provider, and refusing to
        boot over a missing key would block work that does not need one.
        """
        return bool(self.google_application_credentials or self.gemini_api_key)

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
