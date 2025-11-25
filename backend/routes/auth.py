import hashlib
import html
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import create_access_token, get_password_hash, verify_password
from database import get_db
from models import PasswordResetToken, Position, User, UserRole
from permissions import get_default_position
from routes.dependencies import _annotate_user, get_current_user, normalize_email
from schemas import (
    AdminUserCreate,
    AuthConfigResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from settings import (
    ALLOW_PUBLIC_SIGNUP,
    FORGOT_PASSWORD_ENABLED,
    FRONTEND_BASE_URL,
    PASSWORD_RESET_EMAIL_CONTACT,
    PASSWORD_RESET_EMAIL_SUBJECT,
    PASSWORD_RESET_TOKEN_LIFETIME_MINUTES,
)
from utils.mailer import send_email
from utils.timezone import utc_now

router = APIRouter()


def _resolve_position_for_user(
    db: Session,
    role: Optional[UserRole],
    position_id: Optional[str],
) -> Optional[Position]:
    if position_id:
        position = db.query(Position).filter(Position.id == position_id).first()
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        return position
    role = role or UserRole.AGENT
    return get_default_position(db, role)


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _reset_base_url(request: Optional[Request]) -> str:
    if FRONTEND_BASE_URL:
        return FRONTEND_BASE_URL.rstrip("/")
    if request is None:
        return ""
    return str(request.base_url).rstrip("/")


def _build_password_reset_url(raw_token: str, request: Optional[Request]) -> str:
    base = _reset_base_url(request)
    if not base:
        return f"/reset-password?token={raw_token}"
    return f"{base}/reset-password?token={raw_token}"


def _purge_expired_reset_tokens(db: Session) -> None:
    db.query(PasswordResetToken).filter(
        PasswordResetToken.expires_at < utc_now()
    ).delete(synchronize_session=False)


def _send_password_reset_email(email: str, name: Optional[str], reset_url: str) -> None:
    recipient_name = name or "there"
    minutes = PASSWORD_RESET_TOKEN_LIFETIME_MINUTES
    plain_body = (
        f"Hi {recipient_name},\n\n"
        "We received a request to reset the password for your TickleGram account. "
        f"If you made this request, use the link below within {minutes} minutes:\n\n"
        f"{reset_url}\n\n"
        "If you didn't request a password reset, you can safely ignore this email or contact support.\n\n"
        f"Need help? Reach out to us anytime at {PASSWORD_RESET_EMAIL_CONTACT}.\n\n"
        "- The TickleGram Team"
    )
    escaped_name = html.escape(recipient_name)
    html_body = f"""
        <p>Hi {escaped_name},</p>
        <p>We received a request to reset the password for your TickleGram account. If you made this request, click the button below within {minutes} minutes.</p>
        <p style="text-align:center;margin:24px 0;">
            <a href="{reset_url}" style="background:#a855f7;color:#fff;padding:12px 20px;border-radius:999px;text-decoration:none;display:inline-block;">
                Reset password
            </a>
        </p>
        <p>If the button doesn't work, paste this link into your browser:<br/><a href="{reset_url}">{reset_url}</a></p>
        <p>If you didn't request a password reset, you can ignore this email or contact us at <a href="mailto:{PASSWORD_RESET_EMAIL_CONTACT}">{PASSWORD_RESET_EMAIL_CONTACT}</a>.</p>
        <p>- The TickleGram Team</p>
    """
    delivered = send_email(
        subject=PASSWORD_RESET_EMAIL_SUBJECT,
        body_text=plain_body,
        body_html=html_body,
        to_addresses=[email],
    )
    if not delivered:
        # Keep behavior unchanged; only log instead of raising
        from logging import getLogger

        getLogger(__name__).warning(
            "Password reset email not sent (check SMTP config). Recipient=%s", email
        )


@router.post("/auth/register", response_model=UserResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
    )
    position = _resolve_position_for_user(db, user_data.role, user_data.position_id)
    if position:
        new_user.position_id = position.id
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return _annotate_user(new_user)


@router.post("/auth/signup", response_model=UserResponse)
def signup(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    if not ALLOW_PUBLIC_SIGNUP:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Public signup is disabled")
    normalized_email = normalize_email(user_data.email)
    existing_user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = UserRole.AGENT
    new_user = User(
        name=user_data.name,
        email=normalized_email,
        password_hash=get_password_hash(user_data.password),
        role=role
    )
    position = _resolve_position_for_user(db, role, None)
    if position:
        new_user.position_id = position.id
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return _annotate_user(new_user)


@router.get("/auth/config", response_model=AuthConfigResponse)
def auth_config():
    return AuthConfigResponse(
        allow_public_signup=ALLOW_PUBLIC_SIGNUP,
        forgot_password_enabled=FORGOT_PASSWORD_ENABLED,
    )


@router.post("/auth/forgot-password")
def request_password_reset(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    if not FORGOT_PASSWORD_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    normalized_email = normalize_email(payload.email)
    _purge_expired_reset_tokens(db)

    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    raw_token: Optional[str] = None

    if user:
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).delete(synchronize_session=False)

        raw_token = secrets.token_urlsafe(48)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            expires_at=utc_now() + timedelta(minutes=PASSWORD_RESET_TOKEN_LIFETIME_MINUTES),
        )
        db.add(reset_token)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to process request at this time")

    if user and raw_token:
        reset_url = _build_password_reset_url(raw_token, request)
        _send_password_reset_email(user.email, user.name, reset_url)

    return {"message": "If an account exists for that email, a reset link has been sent."}


@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    if not FORGOT_PASSWORD_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    token_hash = _hash_reset_token(payload.token)
    token_record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if not token_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    if token_record.used_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token already used")
    if token_record.expires_at < utc_now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = get_password_hash(payload.new_password)
    token_record.used_at = utc_now()
    db.commit()

    return {"message": "Password reset successfully"}


@router.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(data={"user_id": user.id, "email": user.email})
    user = _annotate_user(user)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
