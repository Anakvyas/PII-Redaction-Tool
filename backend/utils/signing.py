"""Short-lived, tamper-proof download tokens for the local storage backend
(the equivalent of an S3 presigned URL, without needing a real object store)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from core.exceptions import UnauthorizedError


def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def issue_token(storage_uri: str, secret: str, expires_in: int) -> str:
    body = json.dumps({"uri": storage_uri, "exp": int(time.time()) + expires_in}).encode()
    payload_b64 = base64.urlsafe_b64encode(body).decode()
    signature = _sign(payload_b64.encode(), secret)
    return f"{payload_b64}.{signature}"


def verify_token(token: str, secret: str) -> str:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError as exc:
        raise UnauthorizedError("Malformed download token.") from exc

    expected = _sign(payload_b64.encode(), secret)
    if not hmac.compare_digest(expected, signature):
        raise UnauthorizedError("Invalid download token signature.")

    body = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    if body["exp"] < time.time():
        raise UnauthorizedError("Download token has expired.")
    return body["uri"]
