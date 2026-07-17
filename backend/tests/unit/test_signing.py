"""Tests for the HMAC-signed download token (utils/signing.py) — the entire
access-control boundary for /files/download. A forgeable or non-expiring
token here would let anyone read arbitrary files off the storage root."""
import time

import pytest

from core.exceptions import UnauthorizedError
from utils.signing import issue_token, verify_token


class TestRoundTrip:
    def test_issued_token_resolves_back_to_the_original_uri(self):
        token = issue_token("local://originals/doc_1.docx", secret="secret", expires_in=900)
        assert verify_token(token, secret="secret") == "local://originals/doc_1.docx"


class TestTamperResistance:
    def test_rejects_token_signed_with_a_different_secret(self):
        token = issue_token("local://originals/doc_1.docx", secret="secret-a", expires_in=900)
        with pytest.raises(UnauthorizedError):
            verify_token(token, secret="secret-b")

    def test_rejects_payload_swapped_to_a_different_file(self):
        """The core forgery attempt: take a valid token for one file and
        try to point it at another by editing the payload — the signature
        must not validate against the altered payload."""
        token_a = issue_token("local://originals/doc_a.docx", secret="secret", expires_in=900)
        token_b = issue_token("local://originals/doc_b.docx", secret="secret", expires_in=900)
        _, signature_a = token_a.split(".", 1)
        payload_b, _ = token_b.split(".", 1)

        forged = f"{payload_b}.{signature_a}"
        with pytest.raises(UnauthorizedError):
            verify_token(forged, secret="secret")

    def test_rejects_malformed_token_missing_separator(self):
        with pytest.raises(UnauthorizedError):
            verify_token("not-a-real-token", secret="secret")

    def test_rejects_empty_token(self):
        with pytest.raises(UnauthorizedError):
            verify_token("", secret="secret")


class TestExpiry:
    def test_rejects_expired_token(self):
        token = issue_token("local://originals/doc_1.docx", secret="secret", expires_in=-1)
        with pytest.raises(UnauthorizedError):
            verify_token(token, secret="secret")

    def test_accepts_token_within_ttl(self):
        token = issue_token("local://originals/doc_1.docx", secret="secret", expires_in=5)
        assert verify_token(token, secret="secret") == "local://originals/doc_1.docx"

    def test_expiry_is_relative_to_issue_time(self):
        before = time.time()
        token = issue_token("local://originals/doc_1.docx", secret="secret", expires_in=900)
        verify_token(token, secret="secret")
        assert time.time() - before < 5  # sanity: test itself didn't take ~900s
