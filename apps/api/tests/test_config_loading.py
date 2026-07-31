"""Configuration loading.

`.env` sat at the repository root while every command runs from `apps/api`,
and `env_file=".env"` resolves against the *working directory*. So the file was
never read: every setting silently used its default, including `DATABASE_URL`.

That failure mode is invisible. Nothing errors, nothing warns, and the
application runs perfectly on values nobody chose. These tests exist so it
cannot happen again quietly.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import _ENV_FILES, _REPO_ROOT, Settings


def test_the_repo_root_is_where_we_think_it_is() -> None:
    """A wrong `parents[n]` would send every path silently astray."""
    assert (_REPO_ROOT / "docs" / "spec.md").is_file()
    assert (_REPO_ROOT / "apps" / "api" / "pyproject.toml").is_file()


def test_env_paths_are_absolute() -> None:
    """A relative path resolves against the caller's working directory, which
    is exactly the bug this replaced."""
    for path in _ENV_FILES:
        assert Path(path).is_absolute(), f"{path} is relative"


def test_the_root_env_file_is_searched() -> None:
    assert any(Path(p) == _REPO_ROOT / ".env" for p in _ENV_FILES)


def test_settings_load_from_any_working_directory(tmp_path: Path) -> None:
    """The real regression test.

    Constructing Settings from an unrelated directory must produce the same
    values, because the env path no longer depends on where you happen to be.
    """
    import os

    original = Path.cwd()
    try:
        os.chdir(tmp_path)
        elsewhere = Settings()
    finally:
        os.chdir(original)

    here = Settings()
    assert elsewhere.database_url == here.database_url
    assert elsewhere.app_env == here.app_env


def test_the_runtime_role_is_never_the_migration_role() -> None:
    """The two must stay distinct.

    The migration role owns the schema and is a superuser in development, so
    superusers bypass RLS entirely. Pointing the application at it leaves every
    isolation policy in place and completely inert.
    """
    settings = Settings()
    assert settings.database_url != settings.migration_database_url


def test_the_runtime_role_is_not_a_superuser_by_name() -> None:
    """A cheap check that runs without a database, complementing
    `assert_rls_applies` which needs one."""
    settings = Settings()
    role = settings.database_url.split("://", 1)[1].split(":", 1)[0]
    assert role != "marking", (
        "the application is configured to connect as the migration owner, which bypasses RLS"
    )


def test_credentials_default_to_empty_rather_than_a_placeholder() -> None:
    """An unset key must be falsy, not the string 'None' or 'changeme'. A
    truthy placeholder would make `has_ocr_credentials` claim a provider is
    available and fail at the first call instead of at startup."""
    fresh = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    assert fresh.gemini_api_key == ""
    assert fresh.google_application_credentials == ""
    assert fresh.has_ocr_credentials is False
