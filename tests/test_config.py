"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

from optimizer_340b.config import Settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_from_env_with_mock_values(self, mock_env_vars: dict[str, str]) -> None:
        """Settings should load mock environment values correctly."""
        settings = Settings.from_env()

        assert settings.log_level == "DEBUG"
        assert settings.data_dir == Path("/tmp/test_data")
        assert settings.cache_enabled is False
        assert settings.cache_ttl_hours == 1

    def test_from_env_with_defaults(self) -> None:
        """Missing env vars should use sensible defaults."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()

            assert settings.log_level == "INFO"
            assert settings.data_dir == Path("./data/uploads")
            assert settings.cache_enabled is True
            assert settings.cache_ttl_hours == 24

    def test_cache_enabled_false_string(self) -> None:
        """CACHE_ENABLED=false should set cache_enabled to False."""
        with patch.dict(os.environ, {"CACHE_ENABLED": "false"}, clear=False):
            settings = Settings.from_env()
            assert settings.cache_enabled is False

    def test_cache_enabled_true_string(self) -> None:
        """CACHE_ENABLED=true should set cache_enabled to True."""
        with patch.dict(os.environ, {"CACHE_ENABLED": "true"}, clear=False):
            settings = Settings.from_env()
            assert settings.cache_enabled is True

    def test_cache_enabled_case_insensitive(self) -> None:
        """CACHE_ENABLED should be case-insensitive."""
        with patch.dict(os.environ, {"CACHE_ENABLED": "TRUE"}, clear=False):
            settings = Settings.from_env()
            assert settings.cache_enabled is True

        with patch.dict(os.environ, {"CACHE_ENABLED": "False"}, clear=False):
            settings = Settings.from_env()
            assert settings.cache_enabled is False

    def test_ensure_directories_creates_path(self, tmp_path: Path) -> None:
        """ensure_directories should create data directory if it doesn't exist."""
        new_dir = tmp_path / "new_data_dir"
        settings = Settings(
            log_level="INFO",
            data_dir=new_dir,
            cache_enabled=False,
            cache_ttl_hours=1,
        )

        assert not new_dir.exists()
        settings.ensure_directories()
        assert new_dir.exists()

    def test_ensure_directories_idempotent(self, tmp_path: Path) -> None:
        """ensure_directories should be safe to call multiple times."""
        existing_dir = tmp_path / "existing_dir"
        existing_dir.mkdir()

        settings = Settings(
            log_level="INFO",
            data_dir=existing_dir,
            cache_enabled=False,
            cache_ttl_hours=1,
        )

        # Should not raise when called on existing directory
        settings.ensure_directories()
        settings.ensure_directories()
        assert existing_dir.exists()

    def test_cache_ttl_hours_parsing(self) -> None:
        """CACHE_TTL_HOURS should be parsed as integer."""
        with patch.dict(os.environ, {"CACHE_TTL_HOURS": "48"}, clear=False):
            settings = Settings.from_env()
            assert settings.cache_ttl_hours == 48
            assert isinstance(settings.cache_ttl_hours, int)
