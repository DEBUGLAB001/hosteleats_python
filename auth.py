import base64
import hashlib
import hmac
import json
import secrets

import clock

SECRET_KEY = "hosteleats-auth-contest-secret"
TOKEN_TTL_SECONDS = 30
ACCOUNTS = {
    "aarav": {"password": "hostel123", "role": "student", "name": "Aarav Mehta"},
    "canteen": {"password": "kitchen123", "role": "staff", "name": "Canteen Team"},
}
_REVOKED_TOKENS = set()


def _sign(payload_bytes):
    return hmac.new(SECRET_KEY.encode(), payload_bytes, hashlib.sha256).hexdigest()


def login(username, password):
    account = ACCOUNTS.get(str(username or "").strip().lower())
    if not account or not secrets.compare_digest(str(password or ""), account["password"]):
        return None
    payload = {
        "username": str(username).strip().lower(),
        "name": account["name"],
        "role": account["role"],
        "expires_at": clock.now_millis() + TOKEN_TTL_SECONDS * 1000,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = _sign(raw)
    token = f"{b64}.{sig}"
    return {"token": token, "role": account["role"], "name": account["name"], "expires_in": TOKEN_TTL_SECONDS}


def get_session(token):
    if not token or "." not in token or token in _REVOKED_TOKENS:
        return None
    parts = token.split(".", 1)
    if len(parts) != 2:
        return None
    b64, sig = parts
    pad = len(b64) % 4
    if pad:
        b64 += "=" * (4 - pad)
    try:
        raw = base64.urlsafe_b64decode(b64.encode())
    except Exception:
        return None
    expected_sig = _sign(raw)
    if not secrets.compare_digest(sig, expected_sig):
        return None
    try:
        session = json.loads(raw.decode())
    except Exception:
        return None
    if clock.now_seconds() > session["expires_at"]:
        return None
    return dict(session)


def clear_sessions():
    _REVOKED_TOKENS.clear()
