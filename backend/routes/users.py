from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from auth import get_password_hash
from database import get_db
from models import Chat, Position, User, UserRole, UserStatusLog
from permissions import (
    DEFAULT_POSITION_SLUGS,
    PermissionCode,
    get_permission_definitions,
    get_default_position,
    is_super_admin_user,
    user_has_any_permission,
    validate_permissions_payload,
)
from routes.dependencies import (
    _annotate_user,
    _is_assignable_agent,
    get_admin_only_user,
    get_admin_user,
    get_current_user,
    normalize_email,
    require_any_permissions,
    require_permissions,
    require_super_admin,
)
from schemas import (
    AdminUserCreate,
    AdminUserPasswordReset,
    DatabaseOverviewResponse,
    PositionCreate,
    PositionResponse,
    PositionUpdate,
    UserActiveUpdate,
    UserPositionUpdate,
    UserResponse,
    UserRosterEntry,
    normalize_contact_number,
)
from utils.timezone import utc_now
from routes.chat_helpers import reassign_chats_from_inactive_agents

router = APIRouter()


def _normalize_slug(value: str) -> str:
    if not value:
        raise HTTPException(status_code=400, detail="Slug is required")
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise HTTPException(status_code=400, detail="Slug must include alphanumeric characters")
    return slug


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


@router.get("/users", response_model=List[UserResponse])
def list_users(current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    users = db.query(User).options(joinedload(User.position)).all()
    return [_annotate_user(user) for user in users]


@router.get("/users/agents", response_model=List[UserResponse])
def list_agents(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(User).options(joinedload(User.position)).filter(User.role == UserRole.AGENT)
    if not include_inactive:
        query = query.filter(User.is_active.is_(True))
    agents = query.all()
    assignable = [agent for agent in agents if _is_assignable_agent(agent)]
    return [_annotate_user(agent) for agent in assignable]


@router.get("/users/roster", response_model=List[UserRosterEntry])
def user_roster(
    current_user: User = Depends(require_any_permissions(
        PermissionCode.POSITION_ASSIGN,
        PermissionCode.POSITION_MANAGE,
        PermissionCode.CHAT_ASSIGN,
    )),
    db: Session = Depends(get_db)
):
    viewer_is_super_admin = is_super_admin_user(current_user)
    counts = {
        row[0]: row[1]
        for row in (
            db.query(Chat.assigned_to, func.count(Chat.id))
            .filter(Chat.assigned_to.isnot(None))
            .group_by(Chat.assigned_to)
            .all()
        )
        if row[0]
    }
    users = db.query(User).options(joinedload(User.position)).all()
    roster: List[UserRosterEntry] = []
    for user in users:
        annotated = _annotate_user(user)
        user_payload = UserResponse.model_validate(annotated).model_dump()
        if not viewer_is_super_admin:
            position_payload = user_payload.get("position")
            if position_payload and position_payload.get("slug") == DEFAULT_POSITION_SLUGS["super_admin"]:
                user_payload["position"] = None
        user_payload["assigned_chat_count"] = int(counts.get(user.id, 0) or 0)
        roster.append(UserRosterEntry.model_validate(user_payload))
    return roster


@router.patch("/users/{user_id}/active", response_model=UserResponse)
def update_user_active_state(
    user_id: str,
    payload: UserActiveUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.POSITION_MANAGE)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deactivating the last super admin
    if not payload.is_active:
        is_target_super_admin = is_super_admin_user(user)
        if user.id == current_user.id and is_target_super_admin:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own super admin account")
        if is_target_super_admin:
            active_super_admins = (
                db.query(User)
                .filter(User.is_active.is_(True))
                .filter(User.id != user.id)
                .all()
            )
            remaining_super_admins = [u for u in active_super_admins if is_super_admin_user(u)]
            if not remaining_super_admins:
                raise HTTPException(status_code=400, detail="Cannot deactivate the only super admin")

    old_status = user.is_active
    user.is_active = payload.is_active
    db.commit()
    if user.role == UserRole.AGENT and user.is_active is False:
        try:
            reassign_chats_from_inactive_agents(db)
        except Exception:
            pass
    db.refresh(user)

    if old_status != payload.is_active:
        try:
            log_entry = UserStatusLog(
                user_id=user.id,
                changed_by=current_user.email or current_user.id,
                changed_to=payload.is_active,
                note=f"Status changed from {old_status} to {payload.is_active}",
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            db.rollback()
            # Do not block the response; logging is best-effort
            pass
    return UserResponse.model_validate(_annotate_user(user))


@router.post("/admin/users", response_model=UserResponse)
def admin_create_user(
    user_data: AdminUserCreate,
    current_user: User = Depends(require_any_permissions(PermissionCode.USER_INVITE)),
    db: Session = Depends(get_db)
):
    normalized_email = normalize_email(user_data.email or "")
    contact_number = normalize_contact_number(user_data.contact_number)
    emp_id = user_data.emp_id.strip() if user_data.emp_id else None

    if not normalized_email and not contact_number:
        raise HTTPException(status_code=400, detail="Provide at least an email or contact number")

    if normalized_email:
        existing_user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    if contact_number:
        existing_contact = (
            db.query(User)
            .filter(User.contact_number == contact_number)
            .first()
        )
        if existing_contact:
            raise HTTPException(status_code=400, detail="Contact number already registered")
    if emp_id:
        existing_emp = (
            db.query(User)
            .filter(func.lower(User.emp_id) == emp_id.lower())
            .first()
        )
        if existing_emp:
            raise HTTPException(status_code=400, detail="Employee ID already registered")

    new_user = User(
        name=user_data.name.strip(),
        email=normalized_email or None,
        contact_number=contact_number,
        country=user_data.country,
        emp_id=emp_id,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role or UserRole.AGENT,
    )
    position = _resolve_position_for_user(db, user_data.role, user_data.position_id)
    if position:
        new_user.position_id = position.id

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse.model_validate(_annotate_user(new_user))


@router.post("/admin/users/{user_id}/reset-password", response_model=UserResponse)
def admin_reset_password(
    user_id: str,
    payload: AdminUserPasswordReset,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(_annotate_user(user))


@router.get("/dev/db-overview", response_model=DatabaseOverviewResponse)
def get_database_overview(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    from server import _collect_database_overview, _record_schema_snapshot_if_changed, _get_schema_changes_payload  # type: ignore

    overview = _collect_database_overview(db)
    schema_structure = overview.pop("schema_structure", None)
    try:
        _record_schema_snapshot_if_changed(db, schema_structure)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Schema snapshot update failed: %s", exc)
    schema_changes = _get_schema_changes_payload(db)
    return DatabaseOverviewResponse(
        summary=overview["summary"],
        tables=overview["tables"],
        relationships=overview["relationships"],
        storage=overview["storage"],
        schema_changes=schema_changes
    )


@router.get("/positions", response_model=List[PositionResponse])
def list_positions(
    current_user: User = Depends(require_any_permissions(
        "POSITION_MANAGE",
        "POSITION_ASSIGN"
    )),
    db: Session = Depends(get_db)
):
    query = db.query(Position).order_by(Position.created_at.asc())
    if not is_super_admin_user(current_user):
        query = query.filter(Position.slug != DEFAULT_POSITION_SLUGS["super_admin"])
    positions = query.all()
    return positions


@router.post("/positions", response_model=PositionResponse)
def create_position(
    position_data: PositionCreate,
    current_user: User = Depends(require_permissions(PermissionCode.POSITION_MANAGE)),
    db: Session = Depends(get_db)
):
    slug = _normalize_slug(position_data.slug or position_data.name)
    if slug == DEFAULT_POSITION_SLUGS["super_admin"] and not is_super_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admins can create this position")
    existing = db.query(Position).filter(Position.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Position slug already exists")
    position = Position(
        name=position_data.name.strip(),
        slug=slug,
        description=position_data.description,
        is_system=position_data.is_system,
    )
    position.permissions = validate_permissions_payload(position_data.permissions)
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


@router.put("/positions/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: str,
    position_data: PositionUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.POSITION_MANAGE)),
    db: Session = Depends(get_db)
):
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    if position.slug == DEFAULT_POSITION_SLUGS["super_admin"] and not is_super_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admins can edit this position")
    if position_data.name:
        position.name = position_data.name.strip()
    if position_data.description is not None:
        position.description = position_data.description
    if position_data.permissions is not None:
        position.permissions = validate_permissions_payload(position_data.permissions)
    db.commit()
    db.refresh(position)
    return position


@router.delete("/positions/{position_id}")
def delete_position(
    position_id: str,
    current_user: User = Depends(require_permissions("POSITION_MANAGE")),
    db: Session = Depends(get_db)
):
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    if position.is_system:
        raise HTTPException(status_code=400, detail="System positions cannot be deleted")
    in_use = db.query(User).filter(User.position_id == position_id).count()
    if in_use:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a position that is currently assigned to users"
        )
    db.delete(position)
    db.commit()
    return {"success": True, "position_id": position_id}


@router.post("/users/{user_id}/position", response_model=UserResponse)
def assign_position_to_user(
    user_id: str,
    payload: UserPositionUpdate,
    current_user: User = Depends(require_permissions(PermissionCode.POSITION_ASSIGN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id and payload.position_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own position"
        )
    if payload.position_id:
        position = db.query(Position).filter(Position.id == payload.position_id).first()
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        if position.slug == DEFAULT_POSITION_SLUGS["super_admin"] and not is_super_admin_user(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admins can assign this position")
        user.position_id = position.id
    else:
        user.position_id = None
    db.commit()
    db.refresh(user)
    return _annotate_user(user)


@router.get("/permissions/codes")
def list_permission_codes_endpoint(
    current_user: User = Depends(require_permissions(PermissionCode.POSITION_MANAGE))
):
    return get_permission_definitions()
