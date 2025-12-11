import logging
from typing import Optional, Iterable, List

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from auth import decode_access_token
from database import get_db
from models import User, UserRole
from permissions import (
    annotate_user_with_permissions,
    is_super_admin_user,
    user_has_any_permission,
    user_has_permissions,
)

logger = logging.getLogger(__name__)


def _ensure_user_role(user: User) -> User:
    if not user:
        return user
    role = getattr(user, "role", None)
    if isinstance(role, UserRole):
        return user
    if isinstance(role, str):
        normalized = role.strip().lower()
        if normalized in UserRole._value2member_map_:
            user.role = UserRole(normalized)
            return user
    user.role = UserRole.AGENT
    return user


def _annotate_user(user: User) -> User:
    if not user:
        return user
    _ensure_user_role(user)
    annotate_user_with_permissions(user)
    return user


def _is_assignable_agent(user: Optional[User]) -> bool:
    if not user:
        return False
    if user.role != UserRole.AGENT:
        return False
    if getattr(user, "is_active", True) is False:
        return False
    if getattr(user, "can_receive_new_chats", True) is False:
        return False
    return True


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if hasattr(user, "is_active") and user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return _annotate_user(user)


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_admin_only_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if is_super_admin_user(current_user):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Super admin access required"
    )


def require_permissions(*permission_codes: Iterable[str]):
    required_values: List[str] = [
        code.value if hasattr(code, "value") else str(code)
        for code in permission_codes
    ]

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if user_has_permissions(current_user, required_values):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

    return dependency


def require_any_permissions(*permission_codes: Iterable[str]):
    required_values: List[str] = [
        code.value if hasattr(code, "value") else str(code)
        for code in permission_codes
    ]

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if user_has_any_permission(current_user, required_values):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

    return dependency


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()
