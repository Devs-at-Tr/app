import enum
from typing import Dict, Iterable, List, Optional, Sequence, Set

from sqlalchemy.orm import Session

from models import Position, User, UserRole


class PermissionCode(str, enum.Enum):
    CHAT_VIEW_ASSIGNED = "chat:view:assigned"
    CHAT_VIEW_TEAM = "chat:view:team"
    CHAT_VIEW_ALL = "chat:view:all"
    CHAT_MESSAGE = "chat:message"
    CHAT_ASSIGN = "chat:assign"
    TEMPLATE_USE = "template:use"
    TEMPLATE_MANAGE = "template:manage"
    COMMENT_MODERATE = "comment:moderate"
    INTEGRATION_MANAGE = "integration:manage"
    POSITION_MANAGE = "position:manage"
    POSITION_ASSIGN = "position:assign"
    USER_INVITE = "user:invite"
    STATS_VIEW = "stats:view"


ALL_PERMISSION_VALUES: List[str] = [code.value for code in PermissionCode]
ALL_PERMISSION_SET: Set[str] = set(ALL_PERMISSION_VALUES)

PERMISSION_METADATA = {
    PermissionCode.CHAT_VIEW_ASSIGNED.value: {
        "label": "View Assigned Chats",
        "description": "See only the conversations explicitly assigned to the agent."
    },
    PermissionCode.CHAT_VIEW_TEAM.value: {
        "label": "View Team Chats",
        "description": "Access chats assigned to teammates or queues within the same team."
    },
    PermissionCode.CHAT_VIEW_ALL.value: {
        "label": "View All Chats",
        "description": "Full visibility across every FB/IG conversation."
    },
    PermissionCode.CHAT_MESSAGE.value: {
        "label": "Send Messages",
        "description": "Respond to end users within assigned chats."
    },
    PermissionCode.CHAT_ASSIGN.value: {
        "label": "Assign/Reassign Chats",
        "description": "Pick up unassigned chats or reassign between agents."
    },
    PermissionCode.TEMPLATE_USE.value: {
        "label": "Use Templates",
        "description": "Send approved outbound templates."
    },
    PermissionCode.TEMPLATE_MANAGE.value: {
        "label": "Manage Templates",
        "description": "Create, update, submit, and delete messaging templates."
    },
    PermissionCode.COMMENT_MODERATE.value: {
        "label": "Moderate Comments",
        "description": "Hide/reply to Instagram & Facebook comments."
    },
    PermissionCode.INTEGRATION_MANAGE.value: {
        "label": "Manage Integrations",
        "description": "Connect/disconnect Instagram accounts or Facebook pages."
    },
    PermissionCode.POSITION_MANAGE.value: {
        "label": "Manage Positions",
        "description": "Create/update/delete role definitions and permissions."
    },
    PermissionCode.POSITION_ASSIGN.value: {
        "label": "Assign Positions",
        "description": "Attach positions to users."
    },
    PermissionCode.USER_INVITE.value: {
        "label": "Invite Users",
        "description": "Create new agent/admin accounts."
    },
    PermissionCode.STATS_VIEW.value: {
        "label": "View Analytics",
        "description": "See dashboard metrics and reporting."
    },
}


DEFAULT_POSITION_DEFINITIONS = [
    {
        "name": "Super Admin",
        "slug": "super-admin",
        "description": "Unrestricted control over the workspace.",
        "permissions": ALL_PERMISSION_VALUES,
        "is_system": True,
    },
    {
        "name": "Admin",
        "slug": "admin",
        "description": "Primary workspace admin with full control under Super Admins.",
        "permissions": ALL_PERMISSION_VALUES,
        "is_system": True,
    },
    {
        "name": "Supervisor",
        "slug": "supervisor",
        "description": "Oversees teams, reassigns chats, moderates comments, and monitors stats.",
        "permissions": [
            PermissionCode.CHAT_VIEW_ASSIGNED.value,
            PermissionCode.CHAT_VIEW_TEAM.value,
            PermissionCode.CHAT_VIEW_ALL.value,
            PermissionCode.CHAT_MESSAGE.value,
            PermissionCode.CHAT_ASSIGN.value,
            PermissionCode.TEMPLATE_USE.value,
            PermissionCode.COMMENT_MODERATE.value,
            PermissionCode.STATS_VIEW.value,
        ],
        "is_system": True,
    },
    {
        "name": "Agent (Messaging)",
        "slug": "agent-messaging",
        "description": "Handles assigned DM conversations only.",
        "permissions": [
            PermissionCode.CHAT_VIEW_ASSIGNED.value,
            PermissionCode.CHAT_MESSAGE.value,
            PermissionCode.TEMPLATE_USE.value,
        ],
        "is_system": True,
    },
]

DEFAULT_POSITION_SLUGS = {
    "super_admin": "super-admin",
    "admin": "admin",
    "supervisor": "supervisor",
    "agent": "agent-messaging",
    UserRole.ADMIN: "admin",
    UserRole.AGENT: "agent-messaging",
}


def normalize_permissions(codes: Optional[Iterable[str]]) -> List[str]:
    if not codes:
        return []
    normalized = set()
    for code in codes:
        if not code:
            continue
        value = str(code).strip()
        if value and (value in ALL_PERMISSION_SET):
            normalized.add(value)
    return sorted(normalized)


def ensure_default_positions(db: Session) -> None:
    """Ensure the baseline positions exist so we can safely assign users."""
    if db is None:
        return
    existing = {
        position.slug: position
        for position in db.query(Position)
        .filter(Position.slug.in_([item["slug"] for item in DEFAULT_POSITION_DEFINITIONS]))
        .all()
    }
    dirty = False
    for definition in DEFAULT_POSITION_DEFINITIONS:
        if definition["slug"] in existing:
            continue
        position = Position(
            name=definition["name"],
            slug=definition["slug"],
            description=definition.get("description"),
            is_system=definition.get("is_system", False),
        )
        position.permissions = definition.get("permissions", [])
        db.add(position)
        dirty = True
    if dirty:
        db.commit()


def get_default_position_slug_for_role(role: UserRole) -> str:
    return DEFAULT_POSITION_SLUGS.get(role, DEFAULT_POSITION_SLUGS["agent"])


def get_position_by_slug(db: Session, slug: str) -> Optional[Position]:
    if not slug:
        return None
    return db.query(Position).filter(Position.slug == slug).first()


def get_default_position(db: Session, role: UserRole) -> Optional[Position]:
    slug = get_default_position_slug_for_role(role)
    position = get_position_by_slug(db, slug)
    if position is None:
        ensure_default_positions(db)
        position = get_position_by_slug(db, slug)
    return position


def validate_permissions_payload(permissions: Optional[Sequence[str]]) -> List[str]:
    return normalize_permissions(permissions)


def get_permission_definitions() -> List[Dict[str, str]]:
    definitions: List[Dict[str, str]] = []
    for code in ALL_PERMISSION_VALUES:
        meta = PERMISSION_METADATA.get(code, {})
        definitions.append(
            {
                "code": code,
                "label": meta.get("label", code),
                "description": meta.get("description", ""),
            }
        )
    return definitions


def get_user_permissions(user: Optional[User]) -> Set[str]:
    if user is None:
        return set()
    # Legacy ADMIN role retains full access
    if user.role == UserRole.ADMIN:
        return set(ALL_PERMISSION_SET)
    permissions: Set[str] = set()
    if getattr(user, "position", None):
        permissions.update(user.position.permissions or [])
    return permissions


def user_has_permissions(user: Optional[User], required: Sequence[str]) -> bool:
    if not required:
        return True
    if user is None:
        return False
    if user.role == UserRole.ADMIN:
        return True
    granted = get_user_permissions(user)
    return all(code in granted for code in required)


def user_has_any_permission(user: Optional[User], options: Sequence[str]) -> bool:
    if not options:
        return True
    if user is None:
        return False
    if user.role == UserRole.ADMIN:
        return True
    granted = get_user_permissions(user)
    return any(code in granted for code in options)


def annotate_user_with_permissions(user: Optional[User]) -> Optional[User]:
    if user is None:
        return None
    setattr(user, "permissions", list(get_user_permissions(user)))
    return user


def ensure_admin_position_assignments(db: Session) -> None:
    """Guarantee that the first admin is Super Admin; rest fall back to Admin position."""
    if db is None:
        return
    ensure_default_positions(db)
    super_position = get_position_by_slug(db, DEFAULT_POSITION_SLUGS["super_admin"])
    admin_position = get_position_by_slug(db, DEFAULT_POSITION_SLUGS["admin"])
    if not super_position or not admin_position:
        return
    admins = (
        db.query(User)
        .filter(User.role == UserRole.ADMIN)
        .order_by(User.created_at.asc())
        .all()
    )
    if not admins:
        return
    changed = False
    primary_admin = admins[0]
    if primary_admin.position_id != super_position.id:
        primary_admin.position_id = super_position.id
        changed = True
    for extra_admin in admins[1:]:
        if extra_admin.position_id != admin_position.id:
            extra_admin.position_id = admin_position.id
            changed = True
    if changed:
        db.commit()


def is_super_admin_user(user: Optional[User]) -> bool:
    if user is None:
        return False
    position = getattr(user, "position", None)
    if position and position.slug == DEFAULT_POSITION_SLUGS["super_admin"]:
        return True
    # Legacy admins without positions retain super-admin authority
    return user.role == UserRole.ADMIN and not position
