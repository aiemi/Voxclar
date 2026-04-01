from datetime import datetime, timedelta, timezone
import hashlib

from jose import JWTError, jwt
import bcrypt
import httpx

from src.config import get_settings


def hash_password(password: str) -> str:
    # bcrypt 限制 72 bytes，用 SHA256 预哈希处理长密码
    pw_bytes = hashlib.sha256(password.encode()).hexdigest().encode()
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    pw_bytes = hashlib.sha256(plain.encode()).hexdigest().encode()
    return bcrypt.checkpw(pw_bytes, hashed.encode())


def create_access_token(subject: str, extra: dict | None = None) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expires, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expires, "type": "refresh"}
    return jwt.encode(payload, settings.REFRESH_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


def decode_refresh_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.REFRESH_SECRET, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


async def verify_google_token(token: str) -> dict:
    """Verify Google ID token and return user info."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        )
        if resp.status_code != 200:
            raise ValueError("Invalid Google token")
        data = resp.json()
        if data.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise ValueError("Token audience mismatch")
        return {
            "google_id": data["sub"],
            "email": data["email"],
            "name": data.get("name", ""),
            "avatar_url": data.get("picture", ""),
        }
