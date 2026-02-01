"""
Authentication router - login, register, refresh tokens, password change
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, redis_client, schemas, utils
from app.config import settings
from app.database import get_db

router = APIRouter()


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


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    """Extract and validate user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = utils.decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    if jti and redis_client.is_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@router.post("/register", response_model=TokenResponse)
def register(request: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    db_user = db.query(models.User).filter(
        (models.User.email == request.email) | (models.User.login == request.login)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or login already registered")

    hashed_password = utils.get_password_hash(request.password)
    preferences_data = request.preferences.model_dump() if request.preferences else {}

    new_user = models.User(
        email=request.email,
        login=request.login,
        password_hash=hashed_password,
        first_name=request.first_name,
        last_name=request.last_name,
        interests=preferences_data.get("interests"),
        budget_preference=preferences_data.get("budget_preference"),
        travel_styles=preferences_data.get("travel_styles"),
        preferences=preferences_data
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
    user = db.query(models.User).filter(
        (models.User.email == request.identifier) | (models.User.login == request.identifier)
    ).first()
    if not user or not utils.verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect credentials")

    token_data = {"sub": str(user.id), "login": user.login}
    access_token, _ = utils.create_access_token(data=token_data)
    refresh_token, refresh_jti = utils.create_refresh_token(data=token_data)

    refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    redis_client.store_refresh_token(str(user.id), refresh_jti, refresh_ttl)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(request: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    payload = utils.decode_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    old_jti = payload.get("jti")

    if not redis_client.validate_refresh_token(user_id, old_jti):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    redis_client.revoke_refresh_token(user_id, old_jti)

    token_data = {"sub": str(user.id), "login": user.login}
    new_access_token, _ = utils.create_access_token(data=token_data)
    new_refresh_token, new_jti = utils.create_refresh_token(data=token_data)

    refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    redis_client.store_refresh_token(user_id, new_jti, refresh_ttl)

    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/password/change")
def change_password(
    request: PasswordChangeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password"""
    if not utils.verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    user.password_hash = utils.get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/logout")
def logout(
    request: LogoutRequest,
    authorization: str | None = Header(None)
):
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
def logout_all(
    current_user: models.User = Depends(get_current_user),
    authorization: str | None = Header(None)
):
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
