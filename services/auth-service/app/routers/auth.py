"""
Authentication router - login, register, refresh tokens, password change
"""

import uuid
from urllib.parse import quote, urlparse

import httpx
from fastapi import APIRouter, Depends, Header
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, redis_client, schemas, utils
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.email import send_password_reset_email
from app.exceptions import AppException

router = APIRouter()

YANDEX_CALLBACK_PATH = "/auth/yandex/callback"


class LoginRequest(BaseModel):
    identifier: str  # email or login
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class LogoutRequest(BaseModel):
    refresh_token: str


def _origin_from_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _host_without_www(origin: str | None) -> str | None:
    if not origin:
        return None
    parsed = urlparse(origin)
    host = parsed.hostname
    if not host:
        return None
    return host[4:] if host.startswith("www.") else host


def _same_domain_with_optional_www(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    left_parsed = urlparse(left)
    right_parsed = urlparse(right)
    return (
        left_parsed.scheme == right_parsed.scheme
        and left_parsed.port == right_parsed.port
        and _host_without_www(left) == _host_without_www(right)
    )


def _allowed_oauth_origins() -> set[str]:
    origins = {_origin_from_url(origin.strip()) for origin in settings.CORS_ORIGINS.split(",")}
    origins.add(_origin_from_url(settings.FRONTEND_URL))
    origins.add(_origin_from_url(settings.YANDEX_REDIRECT_URI))
    return {origin for origin in origins if origin}


def _resolve_yandex_redirect_uri(origin_or_redirect_uri: str | None) -> str | None:
    configured_redirect_uri = settings.YANDEX_REDIRECT_URI
    configured_origin = _origin_from_url(configured_redirect_uri)
    request_origin = _origin_from_url(origin_or_redirect_uri)

    if request_origin and configured_origin and _same_domain_with_optional_www(request_origin, configured_origin):
        return configured_redirect_uri

    if request_origin and request_origin in _allowed_oauth_origins():
        return f"{request_origin}{YANDEX_CALLBACK_PATH}"

    return configured_redirect_uri


def _redirect_uri_with_host(redirect_uri: str, host: str) -> str:
    parsed = urlparse(redirect_uri)
    netloc = host
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


def _paired_www_redirect_uri(redirect_uri: str) -> str | None:
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None

    paired_host = parsed.hostname[4:] if parsed.hostname.startswith("www.") else f"www.{parsed.hostname}"
    return _redirect_uri_with_host(redirect_uri, paired_host)


def _yandex_redirect_uri_candidates(redirect_uri: str) -> list[str]:
    candidates = [redirect_uri]
    paired_redirect_uri = _paired_www_redirect_uri(redirect_uri)
    if paired_redirect_uri and paired_redirect_uri not in candidates:
        candidates.append(paired_redirect_uri)
    return candidates


@router.post("/register", response_model=TokenResponse)
def register(request: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    db_user = (
        db.query(models.User)
        .filter((models.User.email == request.email) | (models.User.login == request.login))
        .first()
    )
    if db_user:
        raise AppException(status_code=400, code="BAD_REQUEST", message="Email or login already registered")

    hashed_password = utils.get_password_hash(request.password)

    new_user = models.User(
        email=request.email, login=request.login, password_hash=hashed_password, onboarding_completed=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token_data = {"sub": str(new_user.id), "login": new_user.login}
    access_token, _ = utils.create_access_token(data=token_data)
    refresh_token, refresh_jti = utils.create_refresh_token(data=token_data)

    refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    redis_client.store_refresh_token(str(new_user.id), refresh_jti, refresh_ttl)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user by email or login"""
    print(f"DEBUG: Login attempt for identifier: {request.identifier}")
    user = (
        db.query(models.User)
        .filter((models.User.email == request.identifier) | (models.User.login == request.identifier))
        .first()
    )

    if not user:
        print(f"DEBUG: User not found for identifier: {request.identifier}")
        raise AppException(status_code=400, code="BAD_REQUEST", message="Incorrect credentials")

    # Handle Yandex-only users who have no password set
    if not user.password_hash:
        print(f"DEBUG: User {user.login} has no password hash (Yandex-only)")
        raise AppException(
            status_code=400,
            code="BAD_REQUEST",
            message="This account uses Yandex login. Please sign in with Yandex ID.",
        )

    if not utils.verify_password(request.password, user.password_hash):
        print(f"DEBUG: Password mismatch for user: {user.login}")
        raise AppException(status_code=400, code="BAD_REQUEST", message="Incorrect credentials")

    print(f"DEBUG: Login successful for user: {user.login}")

    token_data = {"sub": str(user.id), "login": user.login}
    access_token, _ = utils.create_access_token(data=token_data)
    refresh_token, refresh_jti = utils.create_refresh_token(data=token_data)

    refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    redis_client.store_refresh_token(str(user.id), refresh_jti, refresh_ttl)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/yandex/authorize")
def yandex_authorize(origin: str | None = None):
    """Redirect to Yandex OAuth page"""
    if not settings.YANDEX_CLIENT_ID:
        raise AppException(status_code=500, code="INTERNAL_ERROR", message="Yandex OAuth not configured")

    redirect_uri = _resolve_yandex_redirect_uri(origin)
    if not redirect_uri:
        raise AppException(status_code=500, code="INTERNAL_ERROR", message="Redirect URI not configured")

    url = (
        "https://oauth.yandex.ru/authorize"
        f"?response_type=code&client_id={settings.YANDEX_CLIENT_ID}&redirect_uri={quote(redirect_uri, safe='')}"
    )
    return RedirectResponse(url, status_code=302)


class YandexCallbackRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


@router.post("/yandex/callback", response_model=TokenResponse)
async def yandex_callback(request: YandexCallbackRequest, db: Session = Depends(get_db)):
    """Handle Yandex OAuth callback and return tokens"""
    if not settings.YANDEX_CLIENT_ID or not settings.YANDEX_CLIENT_SECRET or not settings.YANDEX_REDIRECT_URI:
        raise AppException(status_code=500, code="INTERNAL_ERROR", message="Yandex OAuth not configured")

    token_url = "https://oauth.yandex.ru/token"
    effective_redirect_uri = _resolve_yandex_redirect_uri(request.redirect_uri)
    if not effective_redirect_uri:
        raise AppException(status_code=500, code="INTERNAL_ERROR", message="Redirect URI not configured")

    async with httpx.AsyncClient() as client:
        access_token = None
        for redirect_uri in _yandex_redirect_uri_candidates(effective_redirect_uri):
            token_resp = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": request.code,
                    "client_id": settings.YANDEX_CLIENT_ID,
                    "client_secret": settings.YANDEX_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                },
            )
            if token_resp.status_code == 200:
                access_token = token_resp.json().get("access_token")
                break

        if not access_token:
            raise AppException(status_code=400, code="BAD_REQUEST", message="Failed to get Yandex token")

        info_url = "https://login.yandex.ru/info"
        info_resp = await client.get(info_url, headers={"Authorization": f"OAuth {access_token}"})
        if info_resp.status_code != 200:
            raise AppException(status_code=400, code="BAD_REQUEST", message="Failed to get Yandex user info")

        user_info = info_resp.json()
        yandex_id = user_info.get("id")
        yandex_email = user_info.get("default_email", f"{yandex_id}@yandex.yandex")
        yandex_login = user_info.get("login")

        user = (
            db.query(models.User)
            .filter((models.User.yandex_id == yandex_id) | (models.User.email == yandex_email))
            .first()
        )

        if user:
            if not user.yandex_id:
                user.yandex_id = yandex_id
                db.commit()
                db.refresh(user)
        else:
            unique_login = yandex_login or f"yandex_{yandex_id}"
            existing_login = db.query(models.User).filter(models.User.login == unique_login).first()
            if existing_login:
                unique_login = f"{unique_login}_{str(uuid.uuid4())[:8]}"

            user = models.User(
                email=yandex_email,
                login=unique_login,
                yandex_id=yandex_id,
                password_hash=None,
                onboarding_completed=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token_data = {"sub": str(user.id), "login": user.login}
        new_access_token, _ = utils.create_access_token(data=token_data)
        new_refresh_token, new_jti = utils.create_refresh_token(data=token_data)

        refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        redis_client.store_refresh_token(str(user.id), new_jti, refresh_ttl)

        return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(request: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    payload = utils.decode_token(request.refresh_token)
    if not payload:
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Invalid token type")

    user_id = payload.get("sub")
    old_jti = payload.get("jti")

    if not user_id or not old_jti:
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Invalid refresh token")

    if not redis_client.validate_refresh_token(user_id, old_jti):
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Refresh token has been revoked")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise AppException(status_code=401, code="UNAUTHORIZED", message="User not found")

    redis_client.revoke_refresh_token(user_id, old_jti)

    token_data = {"sub": str(user.id), "login": user.login}
    new_access_token, _ = utils.create_access_token(data=token_data)
    new_refresh_token, new_jti = utils.create_refresh_token(data=token_data)

    refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    redis_client.store_refresh_token(str(user.id), new_jti, refresh_ttl)

    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/password/change")
def change_password(
    request: PasswordChangeRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Change password"""
    if not current_user.password_hash:
        raise AppException(
            status_code=400, code="BAD_REQUEST", message="Cannot change password for Yandex-linked accounts"
        )
    if not utils.verify_password(request.old_password, current_user.password_hash):
        raise AppException(status_code=400, code="BAD_REQUEST", message="Incorrect old password")

    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise AppException(status_code=404, code="NOT_FOUND", message="User not found")
    user.password_hash = utils.get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/password/forgot")
async def forgot_password(request: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset — always returns 200 to prevent email enumeration"""
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if user and user.password_hash:
        # Generate reset token and store in Redis (20 min TTL)
        reset_token = str(uuid.uuid4())
        redis_client.store_reset_token(reset_token, str(user.id))

        # Send email (async)

        await send_password_reset_email(user.email, reset_token)

    # Always return success to prevent email enumeration
    return {"message": "If this email exists, a reset link has been sent"}


@router.post("/password/reset")
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using token from email"""
    # Validate token
    user_id = redis_client.get_reset_token_user_id(request.token)
    if not user_id:
        raise AppException(status_code=400, code="BAD_REQUEST", message="Invalid or expired reset token")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise AppException(status_code=400, code="BAD_REQUEST", message="User not found")

    # Check new password is not the same as the old one
    if user.password_hash and utils.verify_password(request.new_password, user.password_hash):
        raise AppException(status_code=400, code="BAD_REQUEST", message="New password must differ from the current one")

    # Update password
    user.password_hash = utils.get_password_hash(request.new_password)
    db.commit()

    # Revoke the reset token (one-time use)
    redis_client.revoke_reset_token(request.token)

    # Revoke all refresh tokens for security
    redis_client.revoke_all_user_tokens(str(user.id))

    return {"message": "Password reset successfully"}


@router.post("/logout")
def logout(request: LogoutRequest, authorization: str | None = Header(None)):
    """Logout - revoke refresh token and optionally blacklist access token"""
    payload = utils.decode_token(request.refresh_token)
    if payload and payload.get("type") == "refresh":
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if user_id and jti:
            redis_client.revoke_refresh_token(user_id, jti)

    if authorization and authorization.startswith("Bearer "):
        access_token = authorization.replace("Bearer ", "")
        access_payload = utils.decode_token(access_token)
        if access_payload:
            access_jti = access_payload.get("jti")
            if access_jti:
                ttl = utils.get_token_remaining_ttl(access_token)
                if ttl > 0:
                    redis_client.add_to_blacklist(access_jti, ttl)

    return {"message": "Logged out successfully"}


@router.post("/logout-all")
def logout_all(current_user: models.User = Depends(get_current_user), authorization: str | None = Header(None)):
    """Logout from all devices - revoke all refresh tokens for user"""
    user_id = str(current_user.id)
    revoked_count = redis_client.revoke_all_user_tokens(user_id)

    if authorization and authorization.startswith("Bearer "):
        access_token = authorization.replace("Bearer ", "")
        access_payload = utils.decode_token(access_token)
        if access_payload:
            access_jti = access_payload.get("jti")
            if access_jti:
                ttl = utils.get_token_remaining_ttl(access_token)
                if ttl > 0:
                    redis_client.add_to_blacklist(access_jti, ttl)

    return {"message": f"Logged out from all devices. {revoked_count} sessions revoked."}
