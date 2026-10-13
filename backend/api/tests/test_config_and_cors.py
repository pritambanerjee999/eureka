"""
Tests for security-relevant configuration: JWT secret strength and CORS.

Author: Pritam
Date: 2026-10-12
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import Settings


class TestJwtSecret:
    def test_short_secret_refused(self, monkeypatch):
        """A weak signing secret must stop the service from starting."""
        monkeypatch.setenv("JWT_SECRET", "short")
        with pytest.raises(ValidationError, match="JWT_SECRET"):
            Settings(_env_file=None)

    def test_missing_secret_refused(self, monkeypatch):
        """There is no insecure default any more."""
        monkeypatch.delenv("JWT_SECRET", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_strong_secret_accepted(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "x" * 32)
        assert Settings(_env_file=None).JWT_SECRET == "x" * 32


class TestCorsOrigins:
    def test_parses_comma_separated_list(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://a.test, https://b.test ,")
        assert Settings(_env_file=None).cors_origins == ["http://a.test", "https://b.test"]

    def test_configured_origin_allowed_other_rejected(self):
        """Only the frontend origin gets CORS headers."""
        from main import app

        with TestClient(app) as c:
            ok = c.get("/health", headers={"Origin": "http://localhost:3000"})
            bad = c.get("/health", headers={"Origin": "https://evil.example"})
        assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "access-control-allow-origin" not in bad.headers
