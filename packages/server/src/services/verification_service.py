"""Email verification code service — in-memory store with TTL."""
import random
import string
import time

# { email: { code: str, expires: float, username: str, password: str, referral_code: str | None } }
_pending: dict[str, dict] = {}

CODE_TTL = 600  # 10 minutes


def generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def store_pending(email: str, code: str, username: str, password: str, referral_code: str | None = None):
    _cleanup()
    _pending[email.lower()] = {
        "code": code,
        "expires": time.time() + CODE_TTL,
        "username": username,
        "password": password,
        "referral_code": referral_code,
    }


def verify_code(email: str, code: str) -> dict | None:
    """Verify code and return pending registration data, or None if invalid."""
    _cleanup()
    key = email.lower()
    entry = _pending.get(key)
    if not entry:
        return None
    if entry["code"] != code:
        return None
    if time.time() > entry["expires"]:
        del _pending[key]
        return None
    # Valid — remove and return
    data = _pending.pop(key)
    return {
        "username": data["username"],
        "password": data["password"],
        "referral_code": data["referral_code"],
    }


def _cleanup():
    now = time.time()
    expired = [k for k, v in _pending.items() if now > v["expires"]]
    for k in expired:
        del _pending[k]
