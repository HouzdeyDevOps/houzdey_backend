import time

import jwt

from app.core.config import settings
from app.core.security import create_token, token_revoked_by_marker, verify_token


def _encode(claims, key=None, algorithm=None):
    return jwt.encode(claims, key or settings.SECRET_KEY, algorithm=algorithm or settings.ALGORITHM)


def test_round_trip_and_type_check():
    token = create_token("user@example.com", "access")
    assert verify_token(token, expected_type="access") == "user@example.com"
    assert verify_token(token, expected_type="refresh") is None


def test_expired_token_is_rejected():
    now = int(time.time())
    token = _encode({"sub": "user@example.com", "type": "access", "iat": now - 120, "exp": now - 60})
    assert verify_token(token) is None


def test_tampered_and_wrongly_signed_tokens_are_rejected():
    good = create_token("user@example.com", "access")
    header, payload, signature = good.split(".")
    assert verify_token(f"{header}.{payload}.{signature[:-3]}abc") is None
    assert verify_token(_encode({"sub": "x", "type": "access", "exp": int(time.time()) + 60}, key="other-secret")) is None


def test_unsigned_alg_none_token_is_rejected():
    token = jwt.encode({"sub": "user@example.com", "type": "access", "exp": int(time.time()) + 60}, key=None, algorithm="none")
    assert verify_token(token) is None


def test_garbage_is_rejected():
    assert verify_token("not-a-jwt") is None
    assert verify_token("") is None


def test_integer_claims_from_older_tokens_still_validate():
    # Tokens minted by the previous library carry integer exp/iat; they must keep working.
    now = int(time.time())
    token = _encode({"sub": "user@example.com", "type": "access", "iat": now, "exp": now + 60})
    assert verify_token(token, expected_type="access") == "user@example.com"


def test_marker_rejects_tokens_without_iat():
    token = _encode({"sub": "user@example.com", "type": "access", "exp": int(time.time()) + 60})
    from datetime import datetime
    assert token_revoked_by_marker(token, datetime.utcnow()) is True
