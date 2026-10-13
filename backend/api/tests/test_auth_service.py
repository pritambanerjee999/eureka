"""
Unit tests for password hashing and JWT helpers.

Author: Pritam
Date: 2026-10-12
"""

from datetime import datetime, timedelta, timezone

import jwt

from config import settings
from services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_roundtrip(self):
        """A password should verify against its own hash."""
        encoded = hash_password("correct horse")
        assert verify_password("correct horse", encoded)

    def test_wrong_password_fails(self):
        """A different password should not verify."""
        assert not verify_password("wrong", hash_password("correct horse"))

    def test_hash_is_salted(self):
        """Hashing the same password twice should yield different encodings."""
        assert hash_password("same") != hash_password("same")

    def test_hash_does_not_contain_plaintext(self):
        """The encoded hash must not leak the plaintext."""
        assert "s3cret-pass" not in hash_password("s3cret-pass")

    def test_malformed_hash_returns_false(self):
        """Garbage or truncated hashes should fail verification instead of raising."""
        assert not verify_password("x", "")
        assert not verify_password("x", "scrypt$1$2")
        assert not verify_password("x", "scrypt$16384$8$1$nothex$abcd")

    def test_unknown_scheme_returns_false(self):
        """Hashes from an unknown scheme should not verify."""
        encoded = hash_password("pw").replace("scrypt$", "bcrypt$", 1)
        assert not verify_password("pw", encoded)


class TestAccessTokens:
    def test_token_roundtrip(self):
        """A freshly issued token should decode to its username."""
        assert decode_access_token(create_access_token("alice")) == "alice"

    def test_tampered_token_rejected(self):
        """Altering the token signature should invalidate it."""
        token = create_access_token("alice")
        assert decode_access_token(token[:-2] + ("aa" if token[-2:] != "aa" else "bb")) is None

    def test_wrong_secret_rejected(self):
        """A token signed with another secret should be rejected."""
        token = jwt.encode({"sub": "alice"}, "other-secret", algorithm="HS256")
        assert decode_access_token(token) is None

    def test_expired_token_rejected(self):
        """A token past its exp claim should be rejected."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token = jwt.encode({"sub": "alice", "exp": past}, settings.JWT_SECRET, algorithm="HS256")
        assert decode_access_token(token) is None

    def test_missing_sub_rejected(self):
        """A validly signed token without a sub claim should be rejected."""
        token = jwt.encode({"foo": "bar"}, settings.JWT_SECRET, algorithm="HS256")
        assert decode_access_token(token) is None

    def test_garbage_token_rejected(self):
        """A non-JWT string should be rejected."""
        assert decode_access_token("not-a-jwt") is None
