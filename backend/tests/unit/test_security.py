"""Tests for the X-API-Key dependency (core/security.py) — auth is disabled
in local dev (empty API_KEY) and required once an operator sets one."""
import asyncio

import pytest

from config.settings import Settings
from core.exceptions import UnauthorizedError
from core.security import require_api_key


def _run(coro):
    return asyncio.run(coro)


class TestAuthDisabled:
    def test_no_api_key_configured_allows_any_request(self):
        settings = Settings(API_KEY="")
        # Should not raise, even with no header at all.
        _run(require_api_key(x_api_key=None, settings=settings))


class TestAuthEnabled:
    def test_matching_key_is_accepted(self):
        settings = Settings(API_KEY="s3cr3t-key")
        _run(require_api_key(x_api_key="s3cr3t-key", settings=settings))

    def test_missing_header_is_rejected(self):
        settings = Settings(API_KEY="s3cr3t-key")
        with pytest.raises(UnauthorizedError):
            _run(require_api_key(x_api_key=None, settings=settings))

    def test_wrong_key_is_rejected(self):
        settings = Settings(API_KEY="s3cr3t-key")
        with pytest.raises(UnauthorizedError):
            _run(require_api_key(x_api_key="wrong-key", settings=settings))

    def test_empty_string_header_is_rejected(self):
        settings = Settings(API_KEY="s3cr3t-key")
        with pytest.raises(UnauthorizedError):
            _run(require_api_key(x_api_key="", settings=settings))

    def test_key_is_case_sensitive(self):
        settings = Settings(API_KEY="S3cr3t-Key")
        with pytest.raises(UnauthorizedError):
            _run(require_api_key(x_api_key="s3cr3t-key", settings=settings))

    def test_prefix_of_real_key_is_rejected(self):
        """Guards against a naive comparison that might treat a prefix
        match differently than a full mismatch."""
        settings = Settings(API_KEY="s3cr3t-key")
        with pytest.raises(UnauthorizedError):
            _run(require_api_key(x_api_key="s3cr3t", settings=settings))
