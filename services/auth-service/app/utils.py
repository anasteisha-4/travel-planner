import uuid
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def generate_jti() -> str:
    """Generate a unique JWT ID"""
    return str(uuid.uuid4())


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> tuple[str, str]:
    """Create access token with JTI"""
    to_encode = data.copy()
    jti = generate_jti()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access", "jti": jti})
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def create_refresh_token(data: dict) -> tuple[str, str]:
    """Create refresh token with JTI"""
    to_encode = data.copy()
    jti = generate_jti()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_token_remaining_ttl(token: str) -> int:
    """Get remaining TTL for a token in seconds"""
    payload = decode_token(token)
    if not payload or "exp" not in payload:
        return 0
    exp = datetime.utcfromtimestamp(payload["exp"])
    remaining = (exp - datetime.utcnow()).total_seconds()
    return max(0, int(remaining))
