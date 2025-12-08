from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Header, Request, Query, WebSocket, WebSocketDisconnect, Response
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import List, Optional, Set, Dict, Any, Tuple, Union, Type
from websocket_manager import manager as ws_manager
import os
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
import random
import asyncio
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import re
import requests
import hashlib
import uuid
from database import engine, get_db, Base, SessionLocal
from utils.timezone import utc_now
from migrations.runner import run_all_migrations as ensure_instagram_profile_schema
from models import (
    User,
    InstagramAccount,
    Chat,
    UserRole,
    ChatStatus,
    MessageSender,
    MessageType,
    FacebookPage,
    FacebookPageStatusLog,
    FacebookUser,
    FacebookMessage,
    MessagePlatform,
    MessageTemplate,
    InstagramUser,
    InstagramMessage as InstagramChatMessage,
    InstagramMessageLog,
    InstagramMessageDirection,
    InstagramComment,
    InstagramCommentAction,
    InstagramMarketingEvent,
    InstagramInsight,
    InstagramInsightScope,
    DBSchemaSnapshot,
    DBSchemaChange,
    AssignmentCursor,
    FacebookWebhookEvent
)
from schemas import (
    UserResponse, TokenResponse,
    InstagramConnect, InstagramAccountResponse,
    MessageCreate, MessageResponse,
    ChatAssign, ChatResponse, ChatWithMessages,
    DashboardStats,
    FacebookPageConnect, FacebookPageResponse, FacebookPageUpdate,
    MessageTemplateCreate,
    MessageTemplateUpdate,
    MessageTemplateResponse,
    TemplateSendRequest,
    InstagramSendRequest,
    InstagramCommentCreateRequest,
    InstagramCommentHideRequest,
    InstagramMarketingEventRequest,
    InstagramMarketingEventSchema,
    InstagramCommentSchema,
    InstagramInsightSchema,
)
from pydantic import BaseModel
from auth import verify_password, get_password_hash, create_access_token, decode_access_token
from facebook_api import facebook_client, FacebookMode
from instagram_api import instagram_client, InstagramMode
from permissions import (
    PermissionCode,
    ensure_default_positions,
    ensure_admin_position_assignments,
    user_has_permissions,
    user_has_any_permission,
    validate_permissions_payload,
    get_permission_definitions,
    is_super_admin_user,
    DEFAULT_POSITION_SLUGS
)
from utils.mailer import send_email
from routes import auth as auth_routes
from routes import users as user_routes
from routes.chat_helpers import reassign_chats_from_inactive_agents
from routes.dependencies import get_current_user, get_admin_user, get_admin_only_user, require_super_admin, require_permissions, require_any_permissions, _annotate_user, normalize_email

try:
    import phonenumbers
    from phonenumbers.phonenumberutil import NumberParseException, region_code_for_number
    from phonenumbers import PhoneNumberFormat
except ImportError:  # pragma: no cover
    phonenumbers = None
    NumberParseException = Exception
    region_code_for_number = lambda x: None  # type: ignore
    PhoneNumberFormat = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

ATTACHMENTS_ROOT = ROOT_DIR / "attachments"
INSTAGRAM_ATTACHMENTS_DIR = ATTACHMENTS_ROOT / "instagram"
ATTACHMENTS_ROOT.mkdir(parents=True, exist_ok=True)
INSTAGRAM_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
ATTACHMENT_DOWNLOAD_TIMEOUT = int(os.getenv("ATTACHMENT_DOWNLOAD_TIMEOUT", "20"))
INSTAGRAM_MESSAGE_ID_MAX_LENGTH = 512

INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID") or os.getenv("PAGE_ID") or os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID") or os.getenv("META_APP_ID")
INSTAGRAM_PAGE_ACCESS_TOKEN = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN") or os.getenv("PAGE_ACCESS_TOKEN") or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
INSTAGRAM_VERIFY_TOKEN = os.getenv("VERIFY_TOKEN") or os.getenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN") or os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN")
FACEBOOK_ACCESS_TOKEN_BACKUP = os.getenv("FACEBOOK_ACCESS_TOKEN_BACKUP")

ChatMessageModel = Union[InstagramChatMessage, FacebookMessage]

from settings import (
    ALLOW_PUBLIC_SIGNUP,
    FORGOT_PASSWORD_ENABLED,
    FRONTEND_BASE_URL,
    PASSWORD_RESET_EMAIL_CONTACT,
    PASSWORD_RESET_EMAIL_SUBJECT,
    PASSWORD_RESET_TOKEN_LIFETIME_MINUTES,
)

class DuplicateMobileCheckRequest(BaseModel):
    mobile: str
    country_code: Optional[str] = None
    not_in_group: Optional[str] = None

class PhoneValidationRequest(BaseModel):
    country_code: str
    phone_number: str


def _message_model_for_platform(platform: MessagePlatform) -> Type[ChatMessageModel]:
    return InstagramChatMessage if platform == MessagePlatform.INSTAGRAM else FacebookMessage


def create_chat_message_record(chat: Chat, **kwargs) -> ChatMessageModel:
    """Instantiate the platform-specific chat message model."""
    model = _message_model_for_platform(chat.platform)
    payload: Dict[str, Any] = {
        "chat_id": chat.id,
        "platform": chat.platform,
        **kwargs,
    }
    if chat.platform == MessagePlatform.INSTAGRAM:
        if not chat.instagram_user_id:
            raise ValueError("Instagram chats require instagram_user_id before creating messages")
        payload.setdefault("instagram_user_id", chat.instagram_user_id)
    else:
        if not chat.facebook_user_id:
            raise ValueError("Facebook chats require facebook_user_id before creating messages")
        payload.setdefault("facebook_user_id", chat.facebook_user_id)
    return model(**payload)


def message_query_for_chat(db: Session, chat: Chat):
    """Return a SQLAlchemy query for the chat's platform-specific message table."""
    return db.query(_message_model_for_platform(chat.platform))


def _requires_sqlite_instagram_fallback(db: Session) -> bool:
    bind = getattr(db, "bind", None)
    if bind is None:
        return True
    return bind.dialect.name.lower() == "sqlite"
PIXEL_ID = os.getenv("PIXEL_ID")
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v18.0")
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET") or os.getenv("FACEBOOK_APP_SECRET", "")
INSTAGRAM_APP_SECRET_ALT = os.getenv("INSTAGRAM_APP_SECRET_ALT", "")
DIAGNOSTIC_HMAC_LOGGING = os.getenv("INSTAGRAM_HMAC_DEBUG", "false").lower() in {"1", "true", "yes"}

def _validate_instagram_secret():
    local_logger = logging.getLogger(__name__)
    secret = INSTAGRAM_APP_SECRET
    if not secret or len(secret) < 10 or "${" in secret:
        local_logger.critical("INSTAGRAM_APP_SECRET is missing or invalid. Shutdown to avoid webhook drift.")
        raise RuntimeError("INSTAGRAM_APP_SECRET is missing or invalid")
    suffix = secret[-6:]
    alt_suffix = INSTAGRAM_APP_SECRET_ALT[-6:] if INSTAGRAM_APP_SECRET_ALT else None
    local_logger.info("Instagram app secret suffix: ****%s", suffix)
    if INSTAGRAM_APP_SECRET_ALT:
        local_logger.info("Instagram alternate app secret suffix: ****%s", alt_suffix)

_validate_instagram_secret()

# Ensure schema migrations are up to date before creating tables
try:
    ensure_instagram_profile_schema(engine)
except Exception as migration_exc:
    logging.getLogger(__name__).warning("Instagram profile migration skipped: %s", migration_exc)

# Create database tables
Base.metadata.create_all(bind=engine)

# Ensure default positions exist for role assignment workflows
try:
    with SessionLocal() as bootstrap_session:
        ensure_default_positions(bootstrap_session)
        ensure_admin_position_assignments(bootstrap_session)
except Exception as exc:
    logging.getLogger(__name__).warning("Default position bootstrap skipped: %s", exc)

# Create the main app
app = FastAPI(
    title="TickleGram API",
    # Enable CORS with credentials for WebSocket
    root_path=os.getenv('API_ROOT_PATH', ''),
)

app.mount(
    "/attachments",
    StaticFiles(directory=ATTACHMENTS_ROOT),
    name="attachments"
)


@app.on_event("startup")
async def _start_background_tasks():
    asyncio.create_task(_inactive_agent_reassignment_worker())


# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

@api_router.get("/health")
def healthcheck():
    return {"status": "ok"}

@api_router.post("/admin/check-duplicate-mobile")
def check_duplicate_mobile(
    payload: DuplicateMobileCheckRequest,
    current_user: User = Depends(get_current_user),
):
    admin_url = os.environ.get("ADMIN_URL")
    form_token = os.environ.get("FORM_TOKEN")
    uid = os.environ.get("UID")
    bid = os.environ.get("BID")

    if not admin_url or not form_token or not uid or not bid:
        raise HTTPException(status_code=500, detail="Duplicate check config missing in environment")

    target = admin_url.rstrip("/") + "/routes/contactRoute.php?action=checkDuplicateMobile"

    data = {
        "form_token": form_token,
        "mobile": payload.mobile,
        "country_code": payload.country_code or "",
        "bid": bid,
    }
    if payload.not_in_group:
        data["not_in_group"] = payload.not_in_group

    headers = {
        "uid": uid,
        "bid": bid,
        "Content-Type": "application/json",
    }
    admin_cookie = os.environ.get("ADMIN_COOKIE")
    if admin_cookie:
        headers["Cookie"] = admin_cookie

    try:
        resp = requests.post(
          target,
          json=data,
          headers=headers,
          timeout=10,
        )
        if resp.status_code >= 400:
            logging.warning("Duplicate mobile check bad status %s: %s", resp.status_code, resp.text)
            raise HTTPException(status_code=resp.status_code, detail="Failed to check duplicate mobile")
        try:
            return resp.json()
        except ValueError:
            logging.warning("Duplicate mobile check non-JSON response: %s", resp.text)
            return {"data": [], "error": 1, "error_msg": "Invalid response from admin", "raw": resp.text}
    except requests.RequestException as exc:
        logging.exception("Duplicate mobile check failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to check duplicate mobile")


@api_router.post("/selectEmployee")
async def select_employee(
    response: Response,
    employee_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Select an employee for the current user. If employee_id is not provided,
    use the current user's emp_id. If none exists, do nothing.
    """
    emp = employee_id or getattr(current_user, "emp_id", None)
    if not emp:
        raise HTTPException(status_code=400, detail="Employee ID not available for this user")

    admin_url = os.environ.get("ADMIN_URL")
    form_token = os.environ.get("FORM_TOKEN")
    uid = os.environ.get("UID")
    bid = os.environ.get("BID")

    if not admin_url or not form_token or not uid or not bid:
        raise HTTPException(status_code=500, detail="Employee selection config missing in environment")

    target = admin_url.rstrip("/") + "/routes/employeeRoute.php?action=select"
    data = {
        "form_token": form_token,
        "col": ["id", "user_id"],
        "filter": [["emp_id", "=", emp]],
        "groupby": "emp_id",
    }

    headers = {
        "uid": uid,
        "bid": bid,
        "Content-Type": "application/json",
    }
    admin_cookie = os.environ.get("ADMIN_COOKIE")
    if admin_cookie:
        headers["Cookie"] = admin_cookie

    try:
        resp = requests.post(
            target,
            json=data,
            headers=headers,
            timeout=10,
        )
        if resp.status_code >= 400:
            logging.warning("Select employee bad status %s: %s", resp.status_code, resp.text)
            raise HTTPException(status_code=resp.status_code, detail="Failed to select employee")
        result = resp.json()
        # Stash in session via cookie for downstream use
        if response is not None:
            response.set_cookie(key="selected_employee_id", value=emp, httponly=False, samesite="Lax")
        return result
    except requests.RequestException as exc:
        logging.exception("Select employee failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to select employee")
    
@api_router.post("/validate-phone")
def validate_phone(request: PhoneValidationRequest):
    if phonenumbers is None:
        # Graceful fallback if dependency is missing
        return {
            "valid": False,
            "possible": False,
            "region": None,
            "formatted": {
                "e164": None,
                "international": None,
                "national": None,
            },
            "input": {
                "country_code": request.country_code,
                "phone_number": request.phone_number,
                "combined": f"{request.country_code or ''}{request.phone_number or ''}",
            },
            "message": "Phone validation unavailable (phonenumbers not installed on server)",
        }

    cc = (request.country_code or "").strip()
    number = (request.phone_number or "").strip()
    if not cc.startswith("+"):
        cc = f"+{cc}"
    full = f"{cc}{number}"
    try:
        parsed = phonenumbers.parse(full, None)
    except NumberParseException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # safety net
        logging.exception("Phone validation unexpected error: %s", exc)
        raise HTTPException(status_code=400, detail="Unable to parse phone number")

    is_possible = phonenumbers.is_possible_number(parsed)
    is_valid = phonenumbers.is_valid_number(parsed)
    region = region_code_for_number(parsed)
    e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164) if is_valid else None
    international = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL) if is_valid else None
    national = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL) if is_valid else None

    return {
        "valid": bool(is_valid),
        "possible": bool(is_possible),
        "region": region,
        "formatted": {
            "e164": e164,
            "international": international,
            "national": national,
        },
        "input": {
            "country_code": cc,
            "phone_number": number,
            "combined": full,
        },
        "message": "Valid" if is_valid else "Invalid phone number",
    }

@api_router.get("/countries")
def list_countries(db: Session = Depends(get_db)):
    """
    Lightweight country list sourced from the database for dialing code selection.
    Uses MYSQL_DATABASE_TickleRight schema when provided.
    """
    tickle_db = os.environ.get("MYSQL_DATABASE_TickleRight") or os.environ.get("MYSQL_DATABASE_TICKLERIGHT")
    safe_db = re.sub(r"[^A-Za-z0-9_]", "", tickle_db or "")
    table_ref = f"`{safe_db}`.countries" if safe_db else "countries"

    sql = text(
        f"""
        SELECT id, name, iso2, phonecode, timezones
        FROM {table_ref}
        WHERE phonecode IS NOT NULL AND phonecode <> ''
        ORDER BY name ASC
        """
    )
    try:
        rows = db.execute(sql).fetchall()
    except Exception as exc:
        logging.exception("Failed to fetch countries: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load countries")

    countries = []
    for row in rows:
        data = row._mapping if hasattr(row, "_mapping") else row
        phonecode_raw = str(data.get("phonecode") or "").strip()
        digits = "".join(ch for ch in phonecode_raw if ch.isdigit())
        if not digits:
            continue
        timezones_raw = data.get("timezones")
        try:
            tz_list = json.loads(timezones_raw) if isinstance(timezones_raw, str) else timezones_raw
            if isinstance(tz_list, dict) and "zone_name" in tz_list:
                tz_list = [tz_list]
        except Exception:
            tz_list = []

        zone_names = []
        if isinstance(tz_list, list):
            for tz in tz_list:
                if isinstance(tz, dict) and tz.get("zone_name"):
                    zone_names.append(str(tz["zone_name"]))
                elif isinstance(tz, str):
                    zone_names.append(tz)

        countries.append(
            {
                "id": str(data.get("id")),
                "name": data.get("name"),
                "iso2": (data.get("iso2") or "").upper(),
                "phonecode": f"+{digits}",
                "timezones": zone_names,
            }
        )
    return countries

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _sanitize_path_component(value: Optional[str], fallback: str = "item") -> str:
    if not value:
        return fallback
    sanitized = re.sub(r'[^A-Za-z0-9._-]', '_', value)
    return sanitized or fallback


def _dump_attachments_json(attachments: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    if not attachments:
        return None
    try:
        return json.dumps(attachments)
    except (TypeError, ValueError):
        return None


def _download_instagram_attachment(
    url: str,
    igsid: str,
    message_identifier: str,
    index: int
) -> Optional[str]:
    """Download an Instagram attachment locally and return its relative path."""
    try:
        response = requests.get(url, timeout=ATTACHMENT_DOWNLOAD_TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to download attachment %s: %s", url, exc)
        return None

    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or ".bin"
    sender_component = _sanitize_path_component(igsid, "ig_user")
    message_component = _sanitize_path_component(message_identifier, "message")
    target_dir = INSTAGRAM_ATTACHMENTS_DIR / sender_component / message_component
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{message_component}_{index}{suffix}"
    file_path = target_dir / filename
    try:
        file_path.write_bytes(response.content)
    except Exception as exc:
        logger.warning("Unable to persist attachment %s: %s", file_path, exc)
        return None


async def _inactive_agent_reassignment_worker():
    """Periodically reassign chats away from inactive agents."""
    interval_seconds = int(os.getenv("INACTIVE_AGENT_REASSIGN_INTERVAL", "60"))
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            with SessionLocal() as session:
                moved = reassign_chats_from_inactive_agents(session)
                if moved:
                    logger.info("Reassigned %s chats from inactive agents", moved)
        except Exception as exc:
            logger.warning("Inactive agent reassignment failed: %s", exc)

    relative_path = file_path.relative_to(ATTACHMENTS_ROOT)
    return str(relative_path).replace(os.sep, "/")


def prepare_instagram_attachments(
    igsid: str,
    message_identifier: str,
    attachments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Augment Instagram attachment payloads with local storage metadata."""
    prepared: List[Dict[str, Any]] = []
    for idx, attachment in enumerate(attachments):
        if not isinstance(attachment, dict):
            continue
        payload = attachment.get("payload") or {}
        source_url = payload.get("url") or attachment.get("url")
        entry = dict(attachment)
        entry["payload"] = payload
        if attachment.get("type") == "image" and source_url:
            local_rel_path = _download_instagram_attachment(
                source_url,
                igsid=igsid,
                message_identifier=message_identifier,
                index=idx
            )
            if local_rel_path:
                entry["local_path"] = local_rel_path
                entry["public_url"] = f"/attachments/{local_rel_path}"
        if source_url and not entry.get("public_url"):
            entry["public_url"] = source_url
        prepared.append(entry)
    return prepared


def _get_facebook_page_token(db: Session, page_id: Optional[str]) -> Optional[str]:
    """Return the stored token for a Facebook page if available."""
    if not page_id:
        return None
    page = (
        db.query(FacebookPage)
        .filter(FacebookPage.page_id == page_id, FacebookPage.is_active.is_(True))
        .first()
    )
    if page and page.access_token:
        return page.access_token
    return None


def _resolve_facebook_profile_token(
    db: Session,
    facebook_user_id: Optional[str],
    preferred_page: Optional[FacebookPage] = None,
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Determine the best token to query the Graph API for a Facebook user's profile.

    Order of preference:
    1. Page token from the currently processed page/webhook.
    2. Page token from the most recent chat linked to the Facebook user.
    3. Backup token (FACEBOOK_ACCESS_TOKEN_BACKUP).
    """
    if preferred_page and preferred_page.access_token:
        return preferred_page.access_token, preferred_page.page_id, "current_page"
    if preferred_page and preferred_page.page_id:
        token = _get_facebook_page_token(db, preferred_page.page_id)
        if token:
            return token, preferred_page.page_id, "current_page"

    if facebook_user_id:
        chat = (
            db.query(Chat)
            .filter(Chat.facebook_user_id == facebook_user_id, Chat.facebook_page_id.isnot(None))
            .order_by(Chat.updated_at.desc())
            .first()
        )
        if chat and chat.facebook_page_id:
            token = _get_facebook_page_token(db, chat.facebook_page_id)
            if token:
                return token, chat.facebook_page_id, "chat_history"

    if FACEBOOK_ACCESS_TOKEN_BACKUP:
        return FACEBOOK_ACCESS_TOKEN_BACKUP, None, "backup"
    return None, None, "none"


def _ensure_timezone_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _humanize_bytes(num_bytes: Optional[int]) -> str:
    value = float(num_bytes or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    return f"{value:.2f} {units[idx]}"


def _get_schema_name(db: Session) -> Optional[str]:
    bind = db.get_bind()
    if not bind:
        return None
    dialect = bind.dialect.name.lower()
    if dialect not in {"mysql"}:
        return None
    try:
        return db.execute(text("SELECT DATABASE()")).scalar()
    except Exception as exc:
        logger.warning("Unable to resolve database schema name: %s", exc)
        return None


def _collect_database_overview(db: Session) -> Dict[str, Any]:
    schema_name = _get_schema_name(db)
    summary: Dict[str, Any] = {
        "database_name": schema_name,
        "table_count": 0,
        "total_rows": 0,
        "data_size_bytes": 0,
        "index_size_bytes": 0,
        "total_size_bytes": 0,
        "total_size_readable": "0 B",
        "metadata_supported": bool(schema_name),
        "info_message": None,
        "last_update": None,
    }
    empty_payload = {
        "summary": summary,
        "tables": [],
        "relationships": [],
        "storage": {
            "total_size_bytes": 0,
            "total_size_readable": "0 B",
            "top_tables": [],
        },
        "schema_structure": None,
    }
    if not schema_name:
        summary["info_message"] = "Schema metadata is only available when connected to MySQL."
        return empty_payload

    try:
        tables_result = db.execute(
            text(
                """
                SELECT
                    table_name AS tbl_name,
                    table_rows AS tbl_rows,
                    data_length AS data_len,
                    index_length AS idx_len,
                    create_time AS tbl_create_time,
                    update_time AS tbl_update_time
                FROM information_schema.TABLES
                WHERE table_schema = :schema
                ORDER BY table_name ASC
                """
            ),
            {"schema": schema_name},
        ).mappings().all()

        columns_result = db.execute(
            text(
                """
                SELECT
                    table_name AS tbl_name,
                    column_name AS col_name,
                    ordinal_position AS col_position,
                    column_type AS col_type,
                    is_nullable AS col_nullable,
                    column_default AS col_default,
                    extra AS col_extra,
                    column_key AS col_key
                FROM information_schema.COLUMNS
                WHERE table_schema = :schema
                ORDER BY table_name, ordinal_position
                """
            ),
            {"schema": schema_name},
        ).mappings().all()

        fk_result = db.execute(
            text(
                """
                SELECT
                    table_name AS fk_table,
                    column_name AS fk_column,
                    referenced_table_name AS fk_ref_table,
                    referenced_column_name AS fk_ref_column,
                    constraint_name AS fk_name
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE table_schema = :schema
                  AND referenced_table_name IS NOT NULL
                """
            ),
            {"schema": schema_name},
        ).mappings().all()
    except Exception as exc:
        logger.error("Failed to query information_schema: %s", exc)
        summary["metadata_supported"] = False
        summary["info_message"] = "Unable to query information_schema for metadata."
        return empty_payload

    table_map: Dict[str, Dict[str, Any]] = {}
    last_update: Optional[datetime] = None
    total_rows = 0
    total_data = 0
    total_index = 0

    for row in tables_result:
        name = row["tbl_name"]
        rows = int(row["tbl_rows"] or 0)
        data_len = int(row["data_len"] or 0)
        index_len = int(row["idx_len"] or 0)
        create_time = _ensure_timezone_aware(row["tbl_create_time"])
        update_time = _ensure_timezone_aware(row["tbl_update_time"])
        if update_time and (last_update is None or update_time > last_update):
            last_update = update_time
        elif create_time and (last_update is None or create_time > last_update):
            last_update = create_time
        total_rows += rows
        total_data += data_len
        total_index += index_len
        table_map[name] = {
            "name": name,
            "rows": rows,
            "data_size_bytes": data_len,
            "index_size_bytes": index_len,
            "total_size_bytes": data_len + index_len,
            "data_size_readable": _humanize_bytes(data_len),
            "index_size_readable": _humanize_bytes(index_len),
            "total_size_readable": _humanize_bytes(data_len + index_len),
            "create_time": create_time,
            "update_time": update_time,
            "columns": [],
        }

    for column in columns_result:
        table_name = column["tbl_name"]
        if table_name not in table_map:
            continue
        default_val = column["col_default"]
        if default_val is not None:
            default_val = str(default_val)
        table_map[table_name]["columns"].append(
            {
                "name": column["col_name"],
                "data_type": column["col_type"],
                "nullable": (column["col_nullable"] or "").upper() == "YES",
                "default": default_val,
                "extra": column["col_extra"],
                "key": column["col_key"],
            }
        )

    relationships = [
        {
            "table": fk["fk_table"],
            "column": fk["fk_column"],
            "references_table": fk["fk_ref_table"],
            "references_column": fk["fk_ref_column"],
            "constraint_name": fk["fk_name"],
        }
        for fk in fk_result
        if fk["fk_table"] in table_map
    ]

    summary.update(
        {
            "table_count": len(table_map),
            "total_rows": total_rows,
            "data_size_bytes": total_data,
            "index_size_bytes": total_index,
            "total_size_bytes": total_data + total_index,
            "total_size_readable": _humanize_bytes(total_data + total_index),
            "last_update": last_update,
        }
    )

    tables_list = list(table_map.values())
    storage = {
        "total_size_bytes": summary["total_size_bytes"],
        "total_size_readable": summary["total_size_readable"],
        "top_tables": sorted(
            [
                {
                    "name": table["name"],
                    "size_bytes": table["total_size_bytes"],
                    "size_readable": table["total_size_readable"],
                    "rows": table["rows"],
                }
                for table in tables_list
            ],
            key=lambda item: item["size_bytes"],
            reverse=True,
        )[:5],
    }

    schema_structure = _build_schema_structure_from_metadata(table_map, relationships)

    return {
        "summary": summary,
        "tables": tables_list,
        "relationships": relationships,
        "storage": storage,
        "schema_structure": schema_structure,
    }


def _build_schema_structure_from_metadata(table_map: Dict[str, Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
    schema = {"tables": {}}
    for table_name, meta in table_map.items():
        columns_snapshot = {}
        for column in meta.get("columns", []):
            columns_snapshot[column["name"]] = {
                "data_type": column["data_type"],
                "nullable": column["nullable"],
                "default": column["default"],
                "extra": column["extra"],
                "key": column["key"],
            }
        schema["tables"][table_name] = {
            "columns": columns_snapshot,
            "foreign_keys": [],
        }
    for fk in relationships:
        table_name = fk["table"]
        if table_name not in schema["tables"]:
            continue
        schema["tables"][table_name]["foreign_keys"].append(
            {
                "column": fk["column"],
                "references_table": fk["references_table"],
                "references_column": fk["references_column"],
                "constraint": fk["constraint_name"],
            }
        )
    return schema


def _detect_schema_changes(previous: Dict[str, Any], current: Dict[str, Any]) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    prev_tables = previous.get("tables", {})
    curr_tables = current.get("tables", {})
    prev_table_names = set(prev_tables.keys())
    curr_table_names = set(curr_tables.keys())

    for table in sorted(curr_table_names - prev_table_names):
        changes.append(
            {
                "change_type": "TABLE_ADDED",
                "table_name": table,
                "column_name": None,
                "details": {},
            }
        )

    for table in sorted(prev_table_names - curr_table_names):
        changes.append(
            {
                "change_type": "TABLE_REMOVED",
                "table_name": table,
                "column_name": None,
                "details": {},
            }
        )

    for table in sorted(curr_table_names & prev_table_names):
        prev_columns = prev_tables.get(table, {}).get("columns", {})
        curr_columns = curr_tables.get(table, {}).get("columns", {})
        prev_cols = set(prev_columns.keys())
        curr_cols = set(curr_columns.keys())

        for column in sorted(curr_cols - prev_cols):
            changes.append(
                {
                    "change_type": "COLUMN_ADDED",
                    "table_name": table,
                    "column_name": column,
                    "details": {"new": curr_columns[column]},
                }
            )
        for column in sorted(prev_cols - curr_cols):
            changes.append(
                {
                    "change_type": "COLUMN_REMOVED",
                    "table_name": table,
                    "column_name": column,
                    "details": {"old": prev_columns[column]},
                }
            )
        for column in sorted(curr_cols & prev_cols):
            if curr_columns[column] != prev_columns[column]:
                changes.append(
                    {
                        "change_type": "COLUMN_CHANGED",
                        "table_name": table,
                        "column_name": column,
                        "details": {
                            "old": prev_columns[column],
                            "new": curr_columns[column],
                        },
                    }
                )
    return changes


def _record_schema_snapshot_if_changed(db: Session, schema_structure: Optional[Dict[str, Any]]) -> None:
    if not schema_structure:
        return
    try:
        latest_snapshot = (
            db.query(DBSchemaSnapshot)
            .order_by(DBSchemaSnapshot.created_at.desc())
            .first()
        )
    except Exception as exc:
        logger.warning("Schema snapshot skipped (table missing?): %s", exc)
        return

    current_json = json.dumps(schema_structure, sort_keys=True)
    if not latest_snapshot:
        snapshot = DBSchemaSnapshot(snapshot_json=current_json, comment="Initial snapshot")
        db.add(snapshot)
        db.commit()
        return

    previous_data = {}
    try:
        previous_data = json.loads(latest_snapshot.snapshot_json or "{}")
    except (json.JSONDecodeError, TypeError):
        previous_data = {}

    changes = _detect_schema_changes(previous_data, schema_structure)
    if not changes:
        return

    snapshot = DBSchemaSnapshot(snapshot_json=current_json)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    for change in changes:
        change_record = DBSchemaChange(
            snapshot_id=snapshot.id,
            change_type=change["change_type"],
            table_name=change["table_name"],
            column_name=change.get("column_name"),
            details_json=json.dumps(change.get("details") or {}),
        )
        db.add(change_record)
    db.commit()


def _get_schema_changes_payload(db: Session) -> Dict[str, Any]:
    payload = {
        "latest_snapshot_id": None,
        "latest_snapshot_created_at": None,
        "latest_summary": {},
        "recent_snapshots": [],
    }
    try:
        snapshots = (
            db.query(DBSchemaSnapshot)
            .order_by(DBSchemaSnapshot.created_at.desc())
            .limit(5)
            .all()
        )
    except Exception as exc:
        logger.warning("Unable to load schema change history: %s", exc)
        return payload

    latest_summary_computed = False
    for snapshot in snapshots:
        changes = (
            db.query(DBSchemaChange)
            .filter(DBSchemaChange.snapshot_id == snapshot.id)
            .order_by(DBSchemaChange.id.asc())
            .limit(100)
            .all()
        )
        change_payloads = []
        for change in changes:
            details = {}
            if change.details_json:
                try:
                    details = json.loads(change.details_json)
                except (TypeError, json.JSONDecodeError):
                    details = {}
            change_payloads.append(
                {
                    "change_type": change.change_type,
                    "table_name": change.table_name,
                    "column_name": change.column_name,
                    "details": details,
                }
            )
        payload["recent_snapshots"].append(
            {
                "id": snapshot.id,
                "created_at": _ensure_timezone_aware(snapshot.created_at),
                "changes": change_payloads,
            }
        )
        if not latest_summary_computed and change_payloads:
            payload["latest_snapshot_id"] = snapshot.id
            payload["latest_snapshot_created_at"] = _ensure_timezone_aware(snapshot.created_at)
            payload["latest_summary"] = {
                "new_tables": sum(1 for c in change_payloads if c["change_type"] == "TABLE_ADDED"),
                "dropped_tables": sum(1 for c in change_payloads if c["change_type"] == "TABLE_REMOVED"),
                "columns_changed": sum(
                    1
                    for c in change_payloads
                    if c["change_type"] in {"COLUMN_ADDED", "COLUMN_REMOVED", "COLUMN_CHANGED"}
                ),
                "change_count": len(change_payloads),
            }
            latest_summary_computed = True
    return payload
_CHAT_VIEW_ALL_PERMISSIONS = [
    PermissionCode.CHAT_VIEW_ALL.value,
    PermissionCode.CHAT_VIEW_TEAM.value,
]


def _user_can_view_all_chats(user: User) -> bool:
    if not user:
        return False
    if user.role == UserRole.ADMIN:
        return True
    return user_has_any_permission(user, _CHAT_VIEW_ALL_PERMISSIONS)


def _assert_chat_access(user: User, chat: Chat) -> None:
    if not user or not chat:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if _user_can_view_all_chats(user):
        return
    if chat.assigned_to == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _serialize_user_light(user: Optional[User]) -> Optional[Dict[str, str]]:
    if not user:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }


def _merge_message_metadata(
    existing_json: Optional[str],
    sent_by: Optional[User] = None,
    extra: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    payload: Dict[str, Any] = {}
    if existing_json:
        try:
            payload = json.loads(existing_json)
        except (ValueError, TypeError):
            payload = {}
    if sent_by:
        info = _serialize_user_light(sent_by)
        if info:
            payload["sent_by"] = info
    if extra:
        for key, value in extra.items():
            if value is not None:
                payload[key] = value
    return json.dumps(payload) if payload else None


def _build_reply_metadata(
    db: Session,
    chat: Chat,
    reply_message_id: Optional[str],
    reply_preview: Optional[str]
) -> Dict[str, Any]:
    """Construct reply metadata payload for outgoing messages."""
    if not reply_message_id:
        return {}

    message_model = _message_model_for_platform(chat.platform)
    reply_target = (
        db.query(message_model)
        .filter(
            message_model.id == reply_message_id,
            message_model.chat_id == chat.id
        )
        .first()
    )
    if not reply_target:
        raise HTTPException(status_code=404, detail="Reply target not found")

    sender_value = reply_target.sender.value if isinstance(reply_target.sender, MessageSender) else str(reply_target.sender or "")
    sender_lower = sender_value.lower()
    if sender_lower in {"agent", "instagram_page"}:
        reply_sender_label = "You"
    else:
        if chat.platform == MessagePlatform.FACEBOOK and not chat.facebook_user and chat.facebook_user_id:
            chat.facebook_user = db.query(FacebookUser).filter(FacebookUser.id == chat.facebook_user_id).first()
        if chat.platform == MessagePlatform.INSTAGRAM and not chat.instagram_user and chat.instagram_user_id:
            chat.instagram_user = db.query(InstagramUser).filter(InstagramUser.igsid == chat.instagram_user_id).first()
        reply_sender_label = (
            (chat.facebook_user.name if chat.facebook_user else None)
            or (chat.instagram_user.name if chat.instagram_user else None)
            or chat.username
            or "User"
        )

    preview_text = (reply_preview or reply_target.content or "[attachment]").strip() or "[attachment]"
    if len(preview_text) > 200:
        preview_text = f"{preview_text[:197]}..."

    metadata_payload: Dict[str, Any] = {
        "reply_to": reply_target.id,
        "reply_preview": preview_text,
        "reply_sender": reply_sender_label,
        "reply_sender_type": sender_lower,
    }
    fb_mid = _extract_facebook_mid(getattr(reply_target, "metadata_json", None))
    if fb_mid:
        metadata_payload["reply_facebook_mid"] = fb_mid
    return metadata_payload


def _parse_ads_context_data(raw: Any) -> Optional[Union[Dict[str, Any], str]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        trimmed = raw.strip()
        if not trimmed:
            return None
        try:
            return json.loads(trimmed)
        except (ValueError, TypeError):
            return raw
    return None


def _extract_facebook_mid(metadata_json: Optional[str]) -> Optional[str]:
    """Extract facebook_mid (Graph message id) from metadata json."""
    if not metadata_json:
        return None
    try:
        meta = json.loads(metadata_json)
    except (TypeError, ValueError):
        return None
    return meta.get("facebook_mid") or meta.get("mid")


def _normalize_referral_payload(referral: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(referral, dict) or not referral:
        return None

    normalized: Dict[str, Any] = {}
    for key in (
        "source",
        "type",
        "ref",
        "ad_id",
        "adset_id",
        "campaign_id",
        "product_id",
        "referral_id",
        "source_event"
    ):
        value = referral.get(key)
        if value is not None:
            normalized[key] = value

    referer_uri = referral.get("referer_uri") or referral.get("referrer_uri")
    if referer_uri:
        normalized["referer_uri"] = referer_uri

    destination = referral.get("destination") or referral.get("destination_url")
    if destination:
        normalized["destination"] = destination

    ads_context = _parse_ads_context_data(referral.get("ads_context_data"))
    if ads_context:
        normalized["ads_context_data"] = ads_context
        if isinstance(ads_context, dict):
            for context_key in ("campaign_id", "ad_id", "adset_id", "product_id"):
                context_value = ads_context.get(context_key)
                if context_value and context_key not in normalized:
                    normalized[context_key] = context_value

    is_guest_user = referral.get("is_guest_user")
    if is_guest_user is not None:
        normalized["is_guest_user"] = is_guest_user

    if referral.get("raw_referral"):
        normalized["raw_referral"] = referral.get("raw_referral")

    if normalized:
        normalized.setdefault("raw", referral)
        return normalized
    return None


def _extract_messaging_referral(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(event, dict):
        return None
    candidate = event.get("referral")
    if isinstance(candidate, dict):
        return candidate
    for key in ("message", "postback"):
        nested = event.get(key)
        if isinstance(nested, dict):
            nested_referral = nested.get("referral")
            if isinstance(nested_referral, dict):
                return nested_referral
    return None


def _is_assignable_agent(user: Optional[User]) -> bool:
    if not user or user.role != UserRole.AGENT:
        return False
    if hasattr(user, "is_active") and not user.is_active:
        return False
    position = getattr(user, "position", None)
    if position and position.slug != DEFAULT_POSITION_SLUGS["agent"]:
        return False
    return True

def _get_assignable_agents(db: Session) -> List[User]:
    agents = (
        db.query(User)
        .options(joinedload(User.position))
        .filter(User.role == UserRole.AGENT)
        .filter(User.is_active.is_(True))
        .all()
    )
    return [agent for agent in agents if _is_assignable_agent(agent)]

def _get_assignment_cursor(db: Session, name: str = "default") -> AssignmentCursor:
    query = db.query(AssignmentCursor).filter(AssignmentCursor.name == name)
    bind = getattr(db, "bind", None)
    if bind and bind.dialect.name.lower() != "sqlite":
        query = query.with_for_update(of=AssignmentCursor)
    cursor = query.first()
    if not cursor:
        cursor = AssignmentCursor(name=name)
        db.add(cursor)
        db.flush()
    return cursor

def _assign_chat_round_robin(db: Session, chat: Chat) -> Optional[User]:
    agents = _get_assignable_agents(db)
    if not agents:
        chat.assigned_to = None
        chat.status = ChatStatus.UNASSIGNED
        return None

    cursor = _get_assignment_cursor(db)
    ordered_agents = sorted(
        agents,
        key=lambda agent: (getattr(agent, "created_at", utc_now()), agent.id)
    )
    next_agent = ordered_agents[0]
    if cursor.last_user_id:
        for idx, agent in enumerate(ordered_agents):
            if agent.id == cursor.last_user_id:
                next_agent = ordered_agents[(idx + 1) % len(ordered_agents)]
                break

    chat.assigned_to = next_agent.id
    chat.status = ChatStatus.ASSIGNED
    cursor.last_user_id = next_agent.id
    cursor.updated_at = utc_now()
    return next_agent

def _chat_requires_agent_reply(chat: Chat) -> bool:
    if not chat.last_incoming_at:
        return False
    if not chat.last_outgoing_at:
        return True
    return chat.last_outgoing_at < chat.last_incoming_at


def require_permissions(*permission_codes: PermissionCode):
    required_values = [
        code.value if isinstance(code, PermissionCode) else str(code)
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


def require_any_permissions(*permission_codes: PermissionCode):
    required_values = [
        code.value if isinstance(code, PermissionCode) else str(code)
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


def resolve_instagram_access_token(db: Session, page_id: Optional[str]) -> Optional[str]:
    """Resolve the best access token for an Instagram page."""
    token: Optional[str] = None
    if page_id:
        account = None
        try:
            account = db.query(InstagramAccount).filter(InstagramAccount.page_id == page_id).first()
        except OperationalError as exc:
            logger.warning("DB connection lost while resolving IG access token for page %s: %s", page_id, exc)
            db.rollback()
            try:
                with SessionLocal() as retry_session:
                    account = (
                        retry_session.query(InstagramAccount)
                        .filter(InstagramAccount.page_id == page_id)
                        .first()
                    )
            except Exception as retry_exc:
                logger.error("Retry failed resolving IG access token for page %s: %s", page_id, retry_exc)
        if account and account.access_token:
            token = account.access_token
    if not token:
        token = INSTAGRAM_PAGE_ACCESS_TOKEN
    return token

def gather_dm_notify_users(db: Session, chat: Optional[Chat] = None) -> Set[str]:
    """Collect user IDs that should receive DM notifications."""
    notify_users: Set[str] = set()
    if chat and chat.assigned_to:
        notify_users.add(str(chat.assigned_to))

    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    notify_users.update(str(user.id) for user in admin_users)
    return notify_users


def normalize_message_sender(message: ChatMessageModel) -> None:
    """Ensure message sender has a valid enum value."""
    if not message:
        return
    sender_value = message.sender.value if isinstance(message.sender, MessageSender) else message.sender
    if not sender_value or not str(sender_value).strip():
        message.sender = MessageSender.INSTAGRAM_PAGE


def _extract_attachment_summary(attachments: List[Any]) -> Optional[str]:
    """Return a human-friendly summary for Instagram attachment payloads."""
    if not attachments:
        return None
    try:
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            attachment_type = attachment.get("type")
            payload = attachment.get("payload") or {}
            if attachment_type == "story_mention":
                # Explicit label so story mentions are visible even without message text
                return "Story mention"

            if attachment_type == "template":
                generic = payload.get("generic") or {}
                elements = generic.get("elements") or payload.get("elements") or []
                titles = [element.get("title") for element in elements if isinstance(element, dict) and element.get("title")]
                if titles:
                    return "\n".join(filter(None, titles))
            title = attachment.get("title") or payload.get("title")
            if title:
                return title
        return "[attachment]"
    except Exception:
        return "[attachment]"


def resolve_message_text(raw_text: Optional[str], attachments: List[Any]) -> Optional[str]:
    """Resolve best-effort text for a message, falling back to attachment summary."""
    if raw_text:
        stripped = raw_text.strip()
        if stripped:
            return stripped
    summary = _extract_attachment_summary(attachments)
    return summary


LEAD_FORM_LABELS = [
    r"what\s+is\s+your\s+child's\s+age\s*\??",
    r"what\s+is\s+your\s+primary\s+goal\s+for\s+your\s+child's\s+development\s*\??",
    r"full\s+name\s*:?",
    r"phone\s+number\s*:?",
    r"email\s*:?",
    r"city\s*:?",
]


def is_lead_form_message(text: Optional[str]) -> bool:
    """
    Detect ad/lead-form style blocks so we can avoid agent assignment.
    Heuristic: message has >=3 lines starting with known labels (case-insensitive).
    """
    if not text:
        return False
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    import re

    pattern = re.compile(rf"^({'|'.join(LEAD_FORM_LABELS)})", re.IGNORECASE)
    matches = sum(1 for ln in lines if pattern.search(ln))
    return matches >= 3


def _clear_assignment_for_lead_form(chat: Chat) -> None:
    """Ensure lead-form chats stay unassigned."""
    chat.assigned_agent = None
    chat.assigned_to = None
    chat.status = ChatStatus.UNASSIGNED


def _is_useless_template_attachments(attachments: Optional[List[Any]]) -> bool:
    """
    True when attachments consist solely of template payloads with empty generic/elements,
    which are noisy webhook deliveries that should be ignored.
    """
    if not attachments:
        return False
    cleaned = attachments if isinstance(attachments, list) else [attachments]
    found_template = False
    for att in cleaned:
        if not isinstance(att, dict):
            return False
        if att.get("type") != "template":
            return False
        payload = att.get("payload") or {}
        generic = payload.get("generic") or {}
        elements = generic.get("elements") or payload.get("elements") or []
        if elements:
            return False
        found_template = True
    return found_template


def hydrate_instagram_chat_messages(chat: Optional[Chat], instagram_msgs: List[InstagramMessageLog]) -> None:
    """Fill in message content for Instagram chats using stored attachment payloads."""
    if not chat or chat.platform != MessagePlatform.INSTAGRAM:
        return
    if not chat.messages:
        chat.messages = []
    if not instagram_msgs:
        return

    grouped: Dict[int, List[InstagramMessageLog]] = {}
    for ig_msg in instagram_msgs:
        grouped.setdefault(int(ig_msg.ts), []).append(ig_msg)

    def _normalize_sender(value: Any) -> MessageSender:
        if isinstance(value, MessageSender):
            return value
        try:
            return MessageSender(value)
        except ValueError:
            if hasattr(value, "value"):
                try:
                    return MessageSender(value.value)
                except ValueError:
                    pass
            return MessageSender.AGENT if str(value).lower().startswith("agent") else MessageSender.INSTAGRAM_USER

    def _bucket(sender_value: Any) -> MessageSender:
        sender_enum = _normalize_sender(sender_value)
        return MessageSender.INSTAGRAM_PAGE if sender_enum in {MessageSender.AGENT, MessageSender.INSTAGRAM_PAGE} else MessageSender.INSTAGRAM_USER

    def _find_candidates(ts_value: Optional[int]) -> List[InstagramMessageLog]:
        if ts_value is None:
            return []
        for delta in (0, -1, 1):
            candidates = grouped.get(ts_value + delta)
            if candidates:
                return candidates
        return []

    existing_keys: Set[Tuple[int, MessageSender]] = set()

    for message in chat.messages:
        if message.platform != MessagePlatform.INSTAGRAM:
            continue
        if not hasattr(message, "attachments"):
            message.attachments = []
        content = (message.content or "").strip()
        if content and content.lower() != "[attachment]":
            continue
        ts_value = None
        if message.timestamp:
            ts_value = int(message.timestamp.timestamp())
        candidates = _find_candidates(ts_value)
        if not candidates:
            if ts_value is not None:
                existing_keys.add((ts_value, _bucket(message.sender)))
            continue

        desired_direction = InstagramMessageDirection.OUTBOUND if message.sender in {
            MessageSender.AGENT,
            MessageSender.INSTAGRAM_PAGE
        } else InstagramMessageDirection.INBOUND

        selected = next((rec for rec in candidates if rec.direction == desired_direction), candidates[0])
        selected_ts = int(selected.ts)
        sender_bucket = MessageSender.INSTAGRAM_PAGE if desired_direction == InstagramMessageDirection.OUTBOUND else MessageSender.INSTAGRAM_USER
        existing_keys.add((selected_ts, sender_bucket))
        if not message.timestamp:
            message.timestamp = datetime.fromtimestamp(selected_ts, tz=timezone.utc)
        if message.timestamp:
            existing_keys.add((int(message.timestamp.timestamp()), _bucket(message.sender)))

        attachments: List[Any] = []
        if selected.attachments_json:
            try:
                attachments = json.loads(selected.attachments_json)
            except Exception:
                attachments = []
        else:
            attachments = []

        hydrated_text = resolve_message_text(selected.text, attachments)
        if hydrated_text:
            message.content = hydrated_text
        message.attachments = attachments
        if attachments:
            message.attachments_json = _dump_attachments_json(attachments)

    def _bucket(sender_enum: MessageSender) -> MessageSender:
        return MessageSender.INSTAGRAM_PAGE if sender_enum in {MessageSender.AGENT, MessageSender.INSTAGRAM_PAGE} else MessageSender.INSTAGRAM_USER

    synthetic_messages: List[InstagramChatMessage] = []

    def _ts(msg: InstagramChatMessage) -> datetime:
        if msg.timestamp:
            return msg.timestamp if msg.timestamp.tzinfo else msg.timestamp.replace(tzinfo=timezone.utc)
        return utc_now()

    def _is_nearby_duplicate(content: str, sender: MessageSender, ts_value: int) -> bool:
        """Return True if an existing chat message matches the same sender/content within a generous time window.

        We allow a wide window (72h) to tolerate timezone/clock drift between stored chat messages
        and instagram_message_logs timestamps.
        """
        if not chat.messages:
            return False
        normalized_content = content.strip()
        target_bucket = _bucket(sender)
        for existing in chat.messages:
            existing_bucket = _bucket(existing.sender)
            if existing_bucket != target_bucket:
                continue
            if (existing.content or "").strip() != normalized_content:
                continue
            existing_ts = _ts(existing)
            delta_seconds = abs(existing_ts.timestamp() - ts_value)
            if delta_seconds <= 72 * 3600:  # 72-hour tolerance to absorb timezone/offset differences
                return True
        return False

    for row in instagram_msgs:
        if row.direction == InstagramMessageDirection.OUTBOUND:
            continue
        row_sender = MessageSender.INSTAGRAM_PAGE if row.direction == InstagramMessageDirection.OUTBOUND else MessageSender.INSTAGRAM_USER
        bucket = _bucket(row_sender)
        if (int(row.ts), bucket) in existing_keys:
            continue

        attachments: List[Any] = []
        if row.attachments_json:
            try:
                attachments = json.loads(row.attachments_json)
            except Exception:
                attachments = []
        resolved = resolve_message_text(row.text, attachments) or "[attachment]"
        if _is_nearby_duplicate(resolved, row_sender, int(row.ts)):
            continue
        synthetic = create_chat_message_record(
            chat,
            id=f"ig-history-{row.id}",
            sender=row_sender,
            content=resolved,
            message_type=MessageType.TEXT,
            timestamp=datetime.fromtimestamp(row.ts, tz=timezone.utc),
            is_ticklegram=bool(getattr(row, "is_ticklegram", False)),
            attachments_json=_dump_attachments_json(attachments)
        )
        synthetic.attachments = attachments
        synthetic_messages.append(synthetic)

    if synthetic_messages:
        chat.messages.extend(synthetic_messages)

    chat.messages.sort(key=_ts)

    def _is_synthetic(message: InstagramChatMessage) -> bool:
        msg_id = getattr(message, "id", "") or ""
        return isinstance(msg_id, str) and msg_id.startswith("ig-history-")

    def _dedupe_key(message: InstagramChatMessage) -> str:
        sender_bucket = _bucket(message.sender)
        content_val = (message.content or "").strip()
        ts_val = _ts(message).isoformat()
        return f"{ts_val}|{sender_bucket.value}|{content_val}"

    unique_messages: List[InstagramChatMessage] = []
    seen_real_keys: Set[str] = set()
    seen_synthetic_keys: Set[str] = set()

    for message in chat.messages:
        dedupe_key = _dedupe_key(message)
        if not _is_synthetic(message):
            seen_real_keys.add(dedupe_key)
            unique_messages.append(message)
            continue

        if dedupe_key in seen_real_keys or dedupe_key in seen_synthetic_keys:
            continue

        seen_synthetic_keys.add(dedupe_key)
        unique_messages.append(message)

    prioritized_messages: List[InstagramChatMessage] = []
    ticklegram_keys: Set[str] = set()
    generic_keys: Set[str] = set()

    def _origin_key(msg: InstagramChatMessage) -> str:
        return f"{_ts(msg).isoformat()}|{(msg.content or '').strip().lower()}"

    for message in unique_messages:
        key = _origin_key(message)
        if getattr(message, "is_ticklegram", False):
            ticklegram_keys.add(key)
            prioritized_messages.append(message)
            continue
        if key in ticklegram_keys or key in generic_keys:
            continue
        generic_keys.add(key)
        prioritized_messages.append(message)

    chat.messages = prioritized_messages
    for message in chat.messages:
        has_explicit = hasattr(message, "attachments") and message.attachments
        if not has_explicit:
            raw_json = getattr(message, "attachments_json", None)
            if raw_json:
                try:
                    message.attachments = json.loads(raw_json)
                except Exception:
                    message.attachments = []


def ensure_instagram_user(
    db: Session,
    igsid: str,
    event_datetime: datetime,
    last_message_preview: Optional[str],
    profile_username: Optional[str] = None,
    profile_name: Optional[str] = None
) -> InstagramUser:
    """Create or refresh an InstagramUser row in an idempotent way."""
    def _apply_profile_fields(user: InstagramUser) -> None:
        if profile_username:
            user.username = profile_username
        if profile_name:
            user.name = profile_name

    instagram_user = db.query(InstagramUser).filter(InstagramUser.igsid == igsid).first()
    if instagram_user:
        instagram_user.last_seen_at = event_datetime
        if last_message_preview:
            instagram_user.last_message = last_message_preview
        _apply_profile_fields(instagram_user)
        return instagram_user

    instagram_user = InstagramUser(
        igsid=igsid,
        first_seen_at=event_datetime,
        last_seen_at=event_datetime,
        last_message=last_message_preview
    )
    _apply_profile_fields(instagram_user)
    db.add(instagram_user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        instagram_user = db.query(InstagramUser).filter(InstagramUser.igsid == igsid).first()
        if not instagram_user:
            raise
        instagram_user.last_seen_at = event_datetime
        if last_message_preview:
            instagram_user.last_message = last_message_preview
        _apply_profile_fields(instagram_user)
    return instagram_user

def gather_admin_user_ids(db: Session) -> Set[str]:
    """Return IDs for all admin users."""
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    return {str(user.id) for user in admin_users}

def upsert_instagram_comment(
    db: Session,
    comment_id: str,
    media_id: str,
    author_id: Optional[str],
    text: Optional[str],
    hidden: bool,
    action: InstagramCommentAction,
    mentioned_user_id: Optional[str],
    ts: int,
    attachments: Optional[Dict[str, Any]] = None
) -> InstagramComment:
    """Create or update an Instagram comment record."""
    comment = db.query(InstagramComment).filter(InstagramComment.id == comment_id).first()
    if comment:
        comment.media_id = media_id
        comment.author_id = author_id
        comment.text = text
        comment.hidden = hidden
        comment.action = action
        comment.mentioned_user_id = mentioned_user_id
        comment.ts = ts
        if attachments:
            comment.attachments_json = json.dumps(attachments)
    else:
        comment = InstagramComment(
            id=comment_id,
            media_id=media_id,
            author_id=author_id,
            text=text,
            hidden=hidden,
            action=action,
            mentioned_user_id=mentioned_user_id,
            ts=ts,
            attachments_json=json.dumps(attachments) if attachments else None
        )
        db.add(comment)
    return comment

def resolve_default_instagram_account(db: Session, current_user: Optional[User] = None) -> Optional[InstagramAccount]:
    """Return a default Instagram account for API operations."""
    query = db.query(InstagramAccount)
    if current_user and current_user.role != UserRole.ADMIN:
        query = query.filter(InstagramAccount.user_id == current_user.id)
    return query.first()


def resolve_meta_entity_for_template(
    db: Session,
    template: MessageTemplate,
    current_user: User,
) -> Tuple[str, str]:
    """Determine the Meta entity (page or IG account) and token for a template submission."""
    if template.platform == MessagePlatform.FACEBOOK:
        page = (
            db.query(FacebookPage)
            .filter(FacebookPage.is_active == True)
            .order_by(FacebookPage.connected_at.desc())
            .first()
        )
        if not page:
            raise HTTPException(status_code=400, detail="No active Facebook page found")
        if not page.access_token:
            raise HTTPException(status_code=400, detail="Facebook page access token not configured")
        return page.page_id, page.access_token

    if template.platform == MessagePlatform.INSTAGRAM:
        account = resolve_default_instagram_account(db, current_user)
        if not account:
            account = (
                db.query(InstagramAccount)
                .order_by(InstagramAccount.connected_at.desc())
                .first()
            )
        if not account:
            raise HTTPException(status_code=400, detail="No connected Instagram account found")
        if not account.access_token:
            raise HTTPException(status_code=400, detail="Instagram account access token not configured")
        return account.page_id, account.access_token

    raise HTTPException(status_code=400, detail=f"Unsupported template platform: {template.platform}")

def persist_instagram_insight(
    db: Session,
    scope: InstagramInsightScope,
    entity_id: str,
    metrics: Dict[str, Any],
    period: Optional[str] = None
) -> InstagramInsight:
    """Store an Instagram insight snapshot."""
    insight = InstagramInsight(
        scope=scope,
        entity_id=entity_id,
        period=period,
        metrics_json=json.dumps(metrics),
        fetched_at=utc_now()
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight

def build_insight_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Graph API insight response to a simple metric dictionary."""
    metrics: Dict[str, Any] = {}
    for entry in data.get("data", []):
        name = entry.get("name")
        values = entry.get("values", [])
        latest_value = None
        if values:
            last_entry = values[-1]
            if isinstance(last_entry, dict):
                latest_value = last_entry.get("value")
            else:
                latest_value = last_entry
        metrics[name] = latest_value
    return metrics

# Dependency to get current user from token
async def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return _annotate_user(user)

# ============= INSTAGRAM ENDPOINTS =============

@api_router.get("/instagram/comments")
async def list_instagram_comments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all Instagram comments from posts and reels"""
    try:
        # Get connected Instagram accounts. Super admins can see all.
        accounts = db.query(InstagramAccount).filter(
            InstagramAccount.user_id == current_user.id
        ).all()
        # If agent has comment moderation visibility (or is super admin), allow workspace-wide view
        if not accounts and (is_super_admin_user(current_user) or user_has_permissions(current_user, [PermissionCode.COMMENT_MODERATE])):
            accounts = db.query(InstagramAccount).all()
        print("Accounts : ", accounts)
        if not accounts:
            logger.info(f"No Instagram accounts found for user {current_user.id}")
            return []
        
        all_comments = []
        for account in accounts:
            try:
                if instagram_client.mode == InstagramMode.MOCK:
                    # Mock data for testing including post info
                    comments = [
                        {
                            "id": f"comment_{i}",
                            "username": f"instagram_user_{i}",
                            "text": f"This is a test comment {i}",
                            "timestamp": utc_now().isoformat(),
                            "profile_pic_url": None,
                            "replies": [],
                            "post": {
                                "id": f"post_{i}",
                                "username": account.username,
                                "profile_pic_url": None,
                                "media_type": "REEL" if i % 2 == 0 else "IMAGE",
                                "media_url": f"https://picsum.photos/id/{i}/800",
                                "permalink": f"https://instagram.com/p/mock_{i}",
                                "caption": f"Test post {i} caption",
                                "timestamp": (utc_now() - timedelta(hours=i)).isoformat()
                            }
                        } for i in range(5)
                    ]
                else:
                    # Get comments and associated posts from Instagram Graph API
                    comments = await instagram_client.get_media_comments(
                        page_access_token=account.access_token,
                        user_id=account.page_id,
                        include_media=True
                    )
                    
                    if not isinstance(comments, list):
                        logger.error(f"Unexpected response format from Instagram API for account {account.id}: {comments}")
                        raise ValueError("Invalid response format from Instagram API")
                    
                all_comments.extend(comments)
                
            except Exception as account_error:
                logger.error(f"Error fetching comments for Instagram account {account.id}: {str(account_error)}")
                # Continue with other accounts instead of failing completely
                continue
        
        # Sort comments only if we have any
        if all_comments:
            try:
                return sorted(all_comments, key=lambda x: x["timestamp"], reverse=True)
            except Exception as sort_error:
                logger.error(f"Error sorting comments: {str(sort_error)}")
                # Return unsorted if sorting fails
                return all_comments
        return all_comments
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting Instagram comments for user {current_user.id}: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to fetch Instagram comments",
                "error": error_msg
            }
        )

@api_router.post("/instagram/comments/{comment_id}/reply")
async def reply_to_instagram_comment(
    comment_id: str,
    reply_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reply to an Instagram comment"""
    try:
        # Find the Instagram account that owns the post
        comment_parts = comment_id.split("_")
        if len(comment_parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid comment ID format")
        
        post_id = comment_parts[0]
        account = db.query(InstagramAccount).filter(
            InstagramAccount.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="No Instagram account found")
        
        if instagram_client.mode == InstagramMode.MOCK:
            # Mock reply for testing
            reply = {
                "id": f"reply_{datetime.now().timestamp()}",
                "text": reply_data["text"],
                "timestamp": utc_now().isoformat(),
                "username": account.username
            }
        else:
            # Send reply through Instagram Graph API
            reply = await instagram_client.reply_to_comment(
                page_access_token=account.access_token,
                comment_id=comment_id,
                message=reply_data["text"]
            )
        
        return reply
    except Exception as e:
        logger.error(f"Error replying to Instagram comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/comments/create", response_model=InstagramCommentSchema)
async def create_instagram_comment(
    payload: InstagramCommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a comment on an Instagram media item."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram page configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram page access token not configured")

    result = await instagram_client.create_comment(
        page_access_token=page_access_token,
        media_id=payload.media_id,
        message=payload.message
    )
    if not result.get("success"):
        error = result.get("error", {"message": "Failed to create comment"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to create comment"))

    comment_id = result.get("id") or result.get("comment_id")
    timestamp_seconds = int(utc_now().timestamp())
    author_id = page_id

    comment_record = upsert_instagram_comment(
        db=db,
        comment_id=comment_id,
        media_id=payload.media_id,
        author_id=author_id,
        text=payload.message,
        hidden=False,
        action=InstagramCommentAction.CREATED,
        mentioned_user_id=None,
        ts=timestamp_seconds,
        attachments=None
    )
    db.commit()
    db.refresh(comment_record)

    await ws_manager.broadcast_global({
        "type": "ig_comment",
        "action": comment_record.action.value,
        "media_id": comment_record.media_id,
        "comment_id": comment_record.id,
        "text": comment_record.text,
        "author_id": comment_record.author_id,
        "hidden": comment_record.hidden,
        "timestamp": comment_record.ts,
        "source": "api"
    })

    return InstagramCommentSchema.model_validate(comment_record)

@api_router.post("/comments/hide", response_model=InstagramCommentSchema)
async def hide_instagram_comment(
    payload: InstagramCommentHideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hide or unhide an Instagram comment."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram page configured")
    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram page access token not configured")

    result = await instagram_client.set_comment_visibility(
        page_access_token=page_access_token,
        comment_id=payload.comment_id,
        hide=payload.hide
    )
    if not result.get("success"):
        error = result.get("error", {"message": "Failed to update comment visibility"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to update comment visibility"))

    details = await instagram_client.get_comment_details(page_access_token, payload.comment_id)
    media_id = details.get("media", {}).get("id") if details.get("success") else None
    author_id = None
    if details.get("success"):
        from_data = details.get("from") or details.get("user") or {}
        if isinstance(from_data, dict):
            author_id = from_data.get("id")

    existing = db.query(InstagramComment).filter(InstagramComment.id == payload.comment_id).first()
    if not media_id:
        media_id = existing.media_id if existing else ""

    timestamp_seconds = int(utc_now().timestamp())

    comment_record = upsert_instagram_comment(
        db=db,
        comment_id=payload.comment_id,
        media_id=media_id,
        author_id=author_id if author_id else (existing.author_id if existing else None),
        text=details.get("text") if details.get("success") else (existing.text if existing else None),
        hidden=payload.hide,
        action=InstagramCommentAction.UPDATED,
        mentioned_user_id=existing.mentioned_user_id if existing else None,
        ts=timestamp_seconds,
        attachments=None
    )
    db.commit()
    db.refresh(comment_record)

    await ws_manager.broadcast_global({
        "type": "ig_comment",
        "action": comment_record.action.value,
        "media_id": comment_record.media_id,
        "comment_id": comment_record.id,
        "text": comment_record.text,
        "author_id": comment_record.author_id,
        "hidden": comment_record.hidden,
        "timestamp": comment_record.ts,
        "source": "api"
    })

    return InstagramCommentSchema.model_validate(comment_record)

@api_router.delete("/comments/delete", response_model=Dict[str, Any])
async def delete_instagram_comment(
    comment_id: str = Query(..., description="Comment ID to delete"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an Instagram comment."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram page configured")
    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram page access token not configured")

    result = await instagram_client.delete_comment(
        page_access_token=page_access_token,
        comment_id=comment_id
    )
    if not result.get("success"):
        error = result.get("error", {"message": "Failed to delete comment"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to delete comment"))

    timestamp_seconds = int(utc_now().timestamp())
    existing = db.query(InstagramComment).filter(InstagramComment.id == comment_id).first()
    media_id = existing.media_id if existing else ""

    comment_record = upsert_instagram_comment(
        db=db,
        comment_id=comment_id,
        media_id=media_id,
        author_id=existing.author_id if existing else None,
        text=existing.text if existing else None,
        hidden=True,
        action=InstagramCommentAction.DELETED,
        mentioned_user_id=existing.mentioned_user_id if existing else None,
        ts=timestamp_seconds,
        attachments=None
    )
    db.commit()

    await ws_manager.broadcast_global({
        "type": "ig_comment",
        "action": comment_record.action.value,
        "media_id": comment_record.media_id,
        "comment_id": comment_record.id,
        "text": comment_record.text,
        "author_id": comment_record.author_id,
        "hidden": comment_record.hidden,
        "timestamp": comment_record.ts,
        "source": "api"
    })

    return {"success": True, "comment_id": comment_id}

@api_router.get("/instagram/mentions")
async def list_instagram_mentions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ig_user_id: Optional[str] = Query(None, description="Instagram business account ID to query")
):
    """Fetch media where the business account is mentioned."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = ig_user_id or (account.page_id if account else INSTAGRAM_PAGE_ID)
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram account available for mentions")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram access token not configured")

    mentions = await instagram_client.get_mentions(
        page_access_token=page_access_token,
        user_id=page_id
    )
    if not mentions.get("success"):
        error = mentions.get("error", {"message": "Failed to fetch mentions"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to fetch mentions"))

    payload = {
        "type": "ig_comment",
        "action": "mentioned",
        "media": mentions.get("data", []),
        "timestamp": int(utc_now().timestamp()),
    }
    await ws_manager.broadcast_global(payload)

    return mentions

@api_router.get("/insights/account", response_model=InstagramInsightSchema)
async def get_account_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ig_user_id: Optional[str] = Query(None, description="Instagram business account ID"),
    metrics: str = Query("impressions,reach,profile_views", description="Comma separated list of metrics"),
    period: str = Query("day", description="Insights period e.g. day, week, month")
):
    """Fetch account-level Instagram insights."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = ig_user_id or (account.page_id if account else INSTAGRAM_PAGE_ID)
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram business account configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram access token not configured")

    response = await instagram_client.get_account_insights(
        page_access_token=page_access_token,
        user_id=page_id,
        metrics=metrics,
        period=period
    )
    if not response.get("success"):
        error = response.get("error", {"message": "Failed to fetch insights"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to fetch insights"))

    metric_map = build_insight_metrics(response)
    insight_record = persist_instagram_insight(
        db=db,
        scope=InstagramInsightScope.ACCOUNT,
        entity_id=page_id,
        metrics=metric_map,
        period=period
    )

    await ws_manager.broadcast_global({
        "type": "ig_insights",
        "scope": "account",
        "entity_id": page_id,
        "metrics": metric_map,
        "timestamp": int(insight_record.fetched_at.timestamp())
    })

    return InstagramInsightSchema.model_validate(insight_record)

@api_router.get("/insights/media", response_model=InstagramInsightSchema)
async def get_media_insights(
    media_id: str = Query(..., description="Instagram media ID"),
    metrics: str = Query("impressions,reach,engagement,saved", description="Comma separated metrics"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch media-level Instagram insights."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram business account configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram access token not configured")

    response = await instagram_client.get_media_insights(
        page_access_token=page_access_token,
        media_id=media_id,
        metrics=metrics
    )
    if not response.get("success"):
        error = response.get("error", {"message": "Failed to fetch media insights"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to fetch media insights"))

    metric_map = build_insight_metrics(response)
    insight_record = persist_instagram_insight(
        db=db,
        scope=InstagramInsightScope.MEDIA,
        entity_id=media_id,
        metrics=metric_map
    )

    await ws_manager.broadcast_global({
        "type": "ig_insights",
        "scope": "media",
        "entity_id": media_id,
        "metrics": metric_map,
        "timestamp": int(insight_record.fetched_at.timestamp())
    })

    return InstagramInsightSchema.model_validate(insight_record)

@api_router.get("/insights/story", response_model=InstagramInsightSchema)
async def get_story_insights(
    story_id: str = Query(..., description="Instagram story ID"),
    metrics: str = Query("impressions,reach,exits,replies", description="Comma separated metrics"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch story-level Instagram insights."""
    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    if not page_id:
        raise HTTPException(status_code=400, detail="No Instagram business account configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=400, detail="Instagram access token not configured")

    response = await instagram_client.get_story_insights(
        page_access_token=page_access_token,
        story_id=story_id,
        metrics=metrics
    )
    if not response.get("success"):
        error = response.get("error", {"message": "Failed to fetch story insights"})
        raise HTTPException(status_code=502, detail=error.get("message", "Failed to fetch story insights"))

    metric_map = build_insight_metrics(response)
    insight_record = persist_instagram_insight(
        db=db,
        scope=InstagramInsightScope.STORY,
        entity_id=story_id,
        metrics=metric_map
    )

    await ws_manager.broadcast_global({
        "type": "ig_insights",
        "scope": "story",
        "entity_id": story_id,
        "metrics": metric_map,
        "timestamp": int(insight_record.fetched_at.timestamp())
    })

    return InstagramInsightSchema.model_validate(insight_record)

@api_router.post("/marketing/events", response_model=InstagramMarketingEventSchema)
async def send_marketing_event(
    payload: InstagramMarketingEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Forward marketing events to the Meta Conversions API."""
    pixel_id = payload.pixel_id or PIXEL_ID
    if not pixel_id:
        raise HTTPException(status_code=400, detail="PIXEL_ID is not configured")

    account = resolve_default_instagram_account(db, current_user)
    page_id = account.page_id if account else INSTAGRAM_PAGE_ID
    access_token = resolve_instagram_access_token(db, page_id)
    if not access_token:
        raise HTTPException(status_code=400, detail="Instagram page access token not available")

    # Prepare Conversions API payload
    custom_data = dict(payload.custom_data or {})
    if payload.value is not None:
        custom_data.setdefault("value", payload.value)
    if payload.currency:
        custom_data.setdefault("currency", payload.currency)

    event_entry: Dict[str, Any] = {
        "event_name": payload.event_name,
        "event_time": payload.event_time,
        "user_data": payload.user_data or {},
        "custom_data": custom_data
    }
    if payload.event_source_url:
        event_entry["event_source_url"] = payload.event_source_url
    if payload.action_source:
        event_entry["action_source"] = payload.action_source
    if payload.event_id:
        event_entry["event_id"] = payload.event_id

    event_payload: Dict[str, Any] = {"data": [event_entry]}
    if payload.test_event_code:
        event_payload["test_event_code"] = payload.test_event_code

    result = await instagram_client.send_marketing_event(
        pixel_id=pixel_id,
        access_token=access_token,
        payload=event_payload
    )

    status = "success" if result.get("success") else "failed"
    response_json = result.get("response") if result.get("success") else result.get("error")

    marketing_event = InstagramMarketingEvent(
        event_name=payload.event_name,
        value=payload.value,
        currency=payload.currency,
        pixel_id=pixel_id,
        external_event_id=payload.event_id,
        status=status,
        payload_json=json.dumps(event_payload),
        response_json=json.dumps(response_json) if response_json else None,
        ts=payload.event_time
    )
    db.add(marketing_event)
    db.commit()
    db.refresh(marketing_event)

    await ws_manager.broadcast_global({
        "type": "ig_marketing_event",
        "event_name": payload.event_name,
        "value": payload.value,
        "currency": payload.currency,
        "ts": payload.event_time,
        "status": status
    })

    return InstagramMarketingEventSchema.model_validate(marketing_event)

@api_router.get("/facebook/comments")
async def list_facebook_comments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List Facebook comments in a chat-friendly format."""
    logger.info(f"Fetching Facebook comments for user {current_user.id}")
    try:
        # Get active Facebook pages that the user has access to
        pages = db.query(FacebookPage).filter(
            FacebookPage.user_id == current_user.id,
            FacebookPage.is_active == True,
            FacebookPage.access_token.isnot(None)
        ).all()
        
        if not pages:
            logger.warning(f"No active Facebook pages found for user {current_user.id}")
            return []

        # Log the number of pages being processed
        logger.info(f"Processing {len(pages)} Facebook pages for comments")
        
        # Verify page tokens are valid
        for page in pages:
            if not page.access_token or len(page.access_token) < 50:  # Basic token validation
                logger.error(f"Invalid access token for page {page.page_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid access token for page {page.page_name}. Please reconnect the page."
                )

        all_comments = []
        
        # Process each page with rate limiting
        for page in pages:
            if facebook_client.mode != FacebookMode.REAL:
                continue
                
            try:
                # Get real comments using the new batch method
                logger.info(f"Fetching comments for page {page.page_name} ({page.page_id})")
                page_comments = await facebook_client.get_page_feed_with_comments(
                    page_access_token=page.access_token,
                    page_id=page.page_id
                )
                
                if not page_comments:
                    logger.warning(f"No comments returned for page {page.page_name}")
                    continue
                    
                all_comments.extend(page_comments)
                logger.info(f"Retrieved {len(page_comments)} comments from page {page.page_name}")
                
                # Add rate limiting delay between pages
                if len(pages) > 1:  # Only delay if there are multiple pages
                    await asyncio.sleep(1)  # 1 second delay between pages
                    
            except Exception as e:
                error_msg = str(e)
                if "access token" in error_msg.lower():
                    logger.error(f"Access token error for page {page.page_id}: {error_msg}")
                    # Update page status in database
                    page.is_active = False
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Access token expired for page {page.page_name}. Please reconnect the page."
                    )
                logger.error(f"Error processing page {page.page_id}: {error_msg}")
                continue

        # Sort all comments by timestamp
        all_comments.sort(key=lambda x: x["timestamp"], reverse=True)

        logger.info(f"Returning {len(all_comments)} total comments")
        return all_comments
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions as they already have proper status codes
        raise http_exc
    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Error fetching Facebook comments: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Facebook comments: {error_msg}"
        )

@api_router.post("/facebook/comments/{comment_id}/reply")
async def reply_to_facebook_comment(
    comment_id: str,
    reply_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reply to a Facebook comment"""
    try:
        # Find all Facebook pages the user has access to
        pages = db.query(FacebookPage).all()
        if not pages:
            raise HTTPException(status_code=404, detail="No Facebook pages found")

        if facebook_client.mode == FacebookMode.MOCK:
            logger.info(f"Mock reply to Facebook comment {comment_id}: {reply_data.get('text', '')}")
            return {
                "success": True,
                "comment_id": comment_id,
                "mode": "mock"
            }

        # Try to reply using each page's access token until success
        # (Since we don't store which page the comment belongs to)
        for page in pages:
            try:
                result = await facebook_client.reply_to_comment(
                    page_access_token=page.access_token,
                    comment_id=comment_id,
                    message=reply_data.get("text", "")
                )
                if result.get("success"):
                    return result
            except Exception as e:
                logger.warning(f"Failed to reply using page {page.page_id}: {str(e)}")
                continue

        raise HTTPException(
            status_code=400,
            detail="Could not reply to comment with any available page access token"
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error replying to Facebook comment: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

@api_router.post("/instagram/accounts", response_model=InstagramAccountResponse)
async def connect_instagram_account(
    data: InstagramConnect, 
    current_user: User = Depends(get_admin_only_user), 
    db: Session = Depends(get_db)
):
    """Connect an Instagram Business Account"""
    
    # Check if account already exists
    existing = db.query(InstagramAccount).filter(
        InstagramAccount.page_id == data.page_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Instagram account already connected")
    
    # In REAL mode, verify the account with Instagram API
    if instagram_client.mode == InstagramMode.REAL:
        # Verify access token by fetching account info
        profile = await instagram_client.get_user_profile(
            page_access_token=data.access_token,
            user_id=data.page_id
        )
        
        if not profile.get("success"):
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to verify Instagram account: {profile.get('error', 'Unknown error')}"
            )
        
        username = profile.get("username", data.username or f"ig_user_{data.page_id[:8]}")
    else:
        # Mock mode
        username = data.username or f"ig_user_{data.page_id[:8]}"
    
    # Create new Instagram account
    new_account = InstagramAccount(
        user_id=current_user.id,
        page_id=data.page_id,
        access_token=data.access_token,
        username=username
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    logger.info(f"Instagram account connected: {new_account.page_id} (@{username}) for user {current_user.email}")
    return new_account

@api_router.get("/instagram/accounts", response_model=List[InstagramAccountResponse])
def list_instagram_accounts(current_user: User = Depends(get_admin_only_user), db: Session = Depends(get_db)):
    """List all connected Instagram accounts for current user"""
    accounts = db.query(InstagramAccount).filter(InstagramAccount.user_id == current_user.id).all()
    return accounts

@api_router.get("/instagram/accounts/{account_id}", response_model=InstagramAccountResponse)
def get_instagram_account(
    account_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Get specific Instagram account"""
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")
    
    return account

@api_router.delete("/instagram/accounts/{account_id}")
def delete_instagram_account(
    account_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Delete/disconnect an Instagram account"""
    account = db.query(InstagramAccount).filter(
        InstagramAccount.id == account_id,
        InstagramAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Instagram account not found")
    
    db.delete(account)
    db.commit()
    
    logger.info(f"Deleted Instagram account: {account.page_id} (@{account.username})")
    return {"success": True, "message": "Instagram account disconnected"}

# Instagram Webhook Endpoints
def _verify_instagram_webhook_subscription(hub_mode: str, hub_challenge: str, hub_verify_token: str):
    if instagram_client.verify_webhook_token(hub_mode, hub_verify_token):
        logger.info("Instagram webhook verification successful via client")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge

    if hub_mode == "subscribe" and INSTAGRAM_VERIFY_TOKEN and hub_verify_token == INSTAGRAM_VERIFY_TOKEN:
        logger.info("Instagram webhook verification successful via fallback token")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge

    logger.warning("Instagram webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")

@api_router.get("/webhooks/instagram")
async def verify_instagram_webhook(
    request: Request,
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token")
):
    """Verify Instagram webhook subscription"""
    print("Request received for Instagram webhook verification", request)
    if instagram_client.verify_webhook_token(hub_mode, hub_verify_token):
        return int(hub_challenge)
    else:
        raise HTTPException(status_code=403, detail="Verification failed")
    """Verify Instagram webhook subscription"""
    
    return _verify_instagram_webhook_subscription(hub_mode, hub_challenge, hub_verify_token)

@app.get("/webhook")
async def instagram_dm_verify(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token")
):
    """Meta webhook verification handler for Instagram DMs."""
    return _verify_instagram_webhook_subscription(hub_mode, hub_challenge, hub_verify_token)

async def _handle_instagram_webhook(request: Request, db: Session) -> Dict[str, Any]:
    """Shared webhook handler for Instagram DM events."""
    try:
        body = await request.body()

        signature_sha256 = request.headers.get("X-Hub-Signature-256")
        signature_sha1 = request.headers.get("X-Hub-Signature")
        # if not instagram_client.verify_webhook_signature(body, signature_sha256, signature_sha1):
        #     logger.warning("Invalid Instagram webhook signature")
        #     raise HTTPException(status_code=401, detail="Invalid signature")

        data = await request.json()
        print("Instagram webhook payload:", data)
        logger.info(f"Received Instagram webhook: {data.get('object')}")

        processed_events = 0
        profile_cache: Dict[str, Dict[str, Any]] = {}

        if data.get("object") != "instagram":
            logger.info("Ignoring non-Instagram webhook payload")
            return {"status": "ignored"}

        for entry in data.get("entry", []):
            instagram_account_id = entry.get("id")
            if not instagram_account_id:
                continue
            if str(instagram_account_id) == "0":
                logger.debug("Skipping Meta test webhook entry with id=0")
                continue

            page_access_token = resolve_instagram_access_token(db, instagram_account_id)
            if not page_access_token:
                logger.warning(f"No access token found for Instagram account {instagram_account_id}")
                continue

            for messaging_event in entry.get("messaging", []):
                message_data = messaging_event.get("message")
                if not message_data:
                    continue

                sender_id = messaging_event.get("sender", {}).get("id")
                recipient_id = messaging_event.get("recipient", {}).get("id")
                if not sender_id or not recipient_id:
                    continue

                is_echo = message_data.get("is_echo", False)
                event_app_id = str(message_data.get("app_id") or messaging_event.get("app_id") or "")
                direction = InstagramMessageDirection.OUTBOUND if is_echo or sender_id == instagram_account_id else InstagramMessageDirection.INBOUND
                igsid = sender_id if direction == InstagramMessageDirection.INBOUND else recipient_id

                processed_payload = await instagram_client.process_webhook_message(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    message_data=message_data,
                    instagram_account_id=instagram_account_id
                )

                message_id = processed_payload.get("message_id")
                normalized_message_id = None
                if message_id:
                    if len(message_id) > INSTAGRAM_MESSAGE_ID_MAX_LENGTH:
                        normalized_message_id = f"hash:{hashlib.sha256(message_id.encode('utf-8')).hexdigest()}"
                    else:
                        normalized_message_id = message_id
                raw_timestamp = messaging_event.get("timestamp")
                if not raw_timestamp:
                    raw_timestamp = utc_now().timestamp() * 1000
                timestamp_seconds = int(raw_timestamp / 1000)
                event_datetime = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)

                referral_raw = _extract_messaging_referral(messaging_event)
                referral_payload = _normalize_referral_payload(referral_raw)
                metadata_extra = {"referral": referral_payload} if referral_payload else None
                referral_metadata_json = _merge_message_metadata(None, extra=metadata_extra)

                raw_attachments = processed_payload.get("attachments") or []
                if not isinstance(raw_attachments, list):
                    raw_attachments = [raw_attachments]
                raw_text_content = processed_payload.get("text")
                lead_form = is_lead_form_message(raw_text_content)
                if _is_useless_template_attachments(raw_attachments) and not (raw_text_content or "").strip():
                    logger.info(
                        "Skipping template-only Instagram webhook message igsid=%s mid=%s",
                        igsid,
                        message_id or normalized_message_id,
                    )
                    continue
                attachments = prepare_instagram_attachments(
                    igsid=igsid,
                    message_identifier=normalized_message_id or f"{timestamp_seconds}",
                    attachments=raw_attachments
                )

                profile_data: Optional[Dict[str, Any]] = profile_cache.get(igsid)
                if profile_data is None:
                    fetched_profile = await instagram_client.get_user_profile(
                        page_access_token=page_access_token,
                        user_id=igsid
                    )
                    if fetched_profile.get("success"):
                        profile_data = fetched_profile
                        profile_cache[igsid] = profile_data

                resolved_text = resolve_message_text(raw_text_content, attachments)
                last_message_preview = resolved_text

                profile_username = None
                profile_name = None
                if profile_data:
                    profile_username = profile_data.get("username")
                    profile_name = profile_data.get("name") or profile_username
                if not profile_username:
                    profile_username = processed_payload.get("sender_username")
                if not profile_name:
                    profile_name = processed_payload.get("sender_name") or profile_username

                instagram_user = ensure_instagram_user(
                    db=db,
                    igsid=igsid,
                    event_datetime=event_datetime,
                    last_message_preview=last_message_preview,
                    profile_username=profile_username,
                    profile_name=profile_name
                )

                if normalized_message_id:
                    existing_message = db.query(InstagramMessageLog).filter(
                        InstagramMessageLog.message_id == normalized_message_id
                    ).first()
                    if existing_message:
                        logger.info(
                            "Duplicate Instagram message %s for user %s; skipping event",
                            message_id,
                            igsid
                        )
                        continue

                try:
                    raw_message_json = json.dumps(message_data)
                except (TypeError, ValueError):
                    raw_message_json = None

                is_ticklegram_event = False
                if is_echo and FACEBOOK_APP_ID:
                    is_ticklegram_event = event_app_id == str(FACEBOOK_APP_ID)

                if direction == InstagramMessageDirection.OUTBOUND and is_ticklegram_event:
                    logger.debug(
                        "Skipping outbound echo from TickleGram app for message %s (igsid=%s)",
                        message_id,
                        igsid
                    )
                    continue

                ig_message = InstagramMessageLog(
                    igsid=igsid,
                    message_id=normalized_message_id,
                    direction=direction,
                    text=resolved_text,
                    attachments_json=json.dumps(attachments) if attachments else None,
                    ts=timestamp_seconds,
                    created_at=event_datetime,
                    raw_payload_json=json.dumps(messaging_event),
                    is_ticklegram=is_ticklegram_event,
                    metadata_json=referral_metadata_json
                )
                db.add(ig_message)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    logger.info(
                        "Duplicate instagram_message %s detected; skipping insert",
                        normalized_message_id or message_id
                    )
                    continue


                chat: Optional[Chat] = None
                new_message: Optional[InstagramChatMessage] = None
                existing_chat: Optional[Chat] = None

                if direction == InstagramMessageDirection.INBOUND:
                    chat = db.query(Chat).filter(
                        Chat.instagram_user_id == sender_id,
                        Chat.platform == MessagePlatform.INSTAGRAM,
                        Chat.facebook_page_id == instagram_account_id
                    ).first()

                    if not chat:
                        profile = profile_data
                        if not profile:
                            profile = await instagram_client.get_user_profile(
                                page_access_token=page_access_token,
                                user_id=sender_id
                            )
                            if profile.get("success"):
                                profile_cache[igsid] = profile
                        print("profile", profile)
                        username = (profile or {}).get("username") or (profile or {}).get("name") or f"IG User {sender_id[:8]}"
                        profile_pic_url = (profile or {}).get("profile_pic_url") or (profile or {}).get("profile_pic")
                        if not profile_pic_url:
                            profile_pic_url = f"https://via.placeholder.com/150?text={sender_id[:8]}"

                        instagram_user.username = (profile or {}).get("username") or instagram_user.username
                        instagram_user.name = (profile or {}).get("name") or instagram_user.name

                        chat = Chat(
                            instagram_user_id=sender_id,
                            username=username,
                            profile_pic_url=profile_pic_url,
                            platform=MessagePlatform.INSTAGRAM,
                            facebook_page_id=instagram_account_id,
                            status=ChatStatus.UNASSIGNED
                        )
                        db.add(chat)
                        db.flush()
                        if not lead_form:
                            assigned_agent = _assign_chat_round_robin(db, chat)
                            if assigned_agent:
                                chat.assigned_agent = assigned_agent
                        else:
                            _clear_assignment_for_lead_form(chat)
                    else:
                        if profile_data:
                            updated_username = profile_data.get("username") or profile_data.get("name")
                            if updated_username:
                                chat.username = updated_username
                            updated_pic = profile_data.get("profile_pic_url") or profile_data.get("profile_pic")
                            if updated_pic:
                                chat.profile_pic_url = updated_pic

                    inbound_content = resolved_text or ("[attachment]" if attachments else "")
                    inferred_type = MessageType.IMAGE if attachments else MessageType.TEXT
                    new_message = create_chat_message_record(
                        chat,
                        sender=MessageSender.INSTAGRAM_USER,
                        content=inbound_content,
                        message_type=inferred_type,
                        timestamp=event_datetime,
                        is_ticklegram=False,
                        attachments_json=_dump_attachments_json(attachments),
                        is_lead_form_message=lead_form,
                        metadata_json=referral_metadata_json
                    )
                    new_message.attachments = attachments
                    db.add(new_message)

                    if lead_form:
                        _clear_assignment_for_lead_form(chat)

                    chat.last_message = inbound_content
                    chat.unread_count += 1
                    chat.last_incoming_at = event_datetime
                    chat.updated_at = event_datetime
                    existing_chat = chat
                else:
                    chat = db.query(Chat).filter(
                        Chat.instagram_user_id == igsid,
                        Chat.platform == MessagePlatform.INSTAGRAM,
                        Chat.facebook_page_id == instagram_account_id
                    ).first()

                    if not chat:
                        profile = profile_data
                        if not profile:
                            profile = await instagram_client.get_user_profile(
                                page_access_token=page_access_token,
                                user_id=igsid
                            )
                            if profile.get("success"):
                                profile_cache[igsid] = profile
                        username = (profile or {}).get("username") or (profile or {}).get("name") or f"IG User {igsid[:8]}"
                        profile_pic_url = (profile or {}).get("profile_pic_url") or (profile or {}).get("profile_pic")
                        if not profile_pic_url:
                            profile_pic_url = f"https://via.placeholder.com/150?text={igsid[:8]}"

                        chat = Chat(
                            instagram_user_id=igsid,
                            username=username,
                            profile_pic_url=profile_pic_url,
                            platform=MessagePlatform.INSTAGRAM,
                            facebook_page_id=instagram_account_id,
                            status=ChatStatus.UNASSIGNED
                        )
                        db.add(chat)
                        db.flush()

                    outbound_preview = resolved_text or ("[attachment]" if attachments else "")
                    inferred_type = MessageType.IMAGE if attachments else MessageType.TEXT

                    def _ts_diff_seconds(lhs: Optional[datetime], rhs: Optional[datetime]) -> Optional[float]:
                        if not lhs or not rhs:
                            return None
                        lhs_local = lhs if lhs.tzinfo else lhs.replace(tzinfo=timezone.utc)
                        rhs_local = rhs if rhs.tzinfo else rhs.replace(tzinfo=timezone.utc)
                        return abs((lhs_local - rhs_local).total_seconds())

                    dedup_candidate: Optional[InstagramChatMessage] = None
                    message_model = _message_model_for_platform(chat.platform)
                    recent_agent_messages = (
                        message_query_for_chat(db, chat)
                        .filter(
                            message_model.chat_id == chat.id,
                            message_model.sender == MessageSender.AGENT,
                            message_model.is_ticklegram.is_(True)
                        )
                        .order_by(message_model.timestamp.desc())
                        .limit(5)
                        .all()
                    )
                    for candidate in recent_agent_messages:
                        if (candidate.content or "").strip() != outbound_preview.strip():
                            continue
                        diff_seconds = _ts_diff_seconds(candidate.timestamp, event_datetime)
                        if diff_seconds is not None and diff_seconds <= 30:
                            dedup_candidate = candidate
                            break

                    if dedup_candidate:
                        new_message = dedup_candidate
                        new_message.attachments = attachments or getattr(new_message, "attachments", [])
                        if attachments:
                            new_message.attachments_json = _dump_attachments_json(attachments)
                        if metadata_extra:
                            new_message.metadata_json = _merge_message_metadata(
                                new_message.metadata_json,
                                extra=metadata_extra
                            )
                    else:
                        new_message = create_chat_message_record(
                            chat,
                            sender=MessageSender.INSTAGRAM_PAGE,
                            content=outbound_preview,
                            message_type=inferred_type,
                            timestamp=event_datetime,
                            is_ticklegram=is_ticklegram_event,
                            attachments_json=_dump_attachments_json(attachments),
                            metadata_json=referral_metadata_json
                        )
                        new_message.attachments = attachments
                        db.add(new_message)

                    chat.last_message = outbound_preview
                    chat.last_outgoing_at = event_datetime
                    chat.updated_at = event_datetime
                    existing_chat = chat

                db.flush()
                db.commit()

                db.refresh(ig_message)
                if new_message:
                    db.refresh(new_message)

                notify_users = set()
                if direction == InstagramMessageDirection.INBOUND:
                    notify_users = gather_dm_notify_users(db, chat)
                else:
                    if new_message:
                        existing_chat = existing_chat or db.query(Chat).filter(
                            Chat.instagram_user_id == igsid,
                            Chat.platform == MessagePlatform.INSTAGRAM
                        ).first()
                        notify_users = gather_dm_notify_users(db, existing_chat)

                # Broadcast legacy chat payload for inbound messages
                if new_message and notify_users:
                    message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")
                    await ws_manager.broadcast_to_users(notify_users, {
                        "type": "new_message",
                        "chat_id": str((existing_chat or chat).id),
                        "platform": (existing_chat or chat).platform.value,
                        "sender_id": sender_id,
                        "message": message_payload
                    })

                # Broadcast DM payload
                dm_payload = {
                    "type": "ig_dm",
                    "legacy_type": "instagram_dm",
                    "direction": direction.value,
                    "igsid": igsid,
                    "text": resolved_text,
                    "attachments": attachments,
                    "timestamp": timestamp_seconds,
                    "message_id": ig_message.id,
                    "page_id": instagram_account_id,
                    "delivery_status": "received" if direction == InstagramMessageDirection.INBOUND else "delivered"
                }
                if referral_payload:
                    dm_payload["referral"] = referral_payload

                if notify_users:
                    await ws_manager.broadcast_to_users(notify_users, dm_payload)

                processed_events += 1

            for change in entry.get("changes", []):
                field = change.get("field")
                value = change.get("value", {})
                if field not in {"comments", "mention", "mentions"}:
                    continue

                comment_id = value.get("id") or value.get("comment_id")
                media_id = value.get("media_id") or value.get("parent_id") or value.get("post_id")
                if not comment_id or not media_id:
                    logger.debug("Skipping comment webhook change lacking IDs: %s", value)
                    continue

                verb = value.get("verb") or value.get("action") or "add"
                action_map = {
                    "add": InstagramCommentAction.CREATED,
                    "edited": InstagramCommentAction.UPDATED,
                    "update": InstagramCommentAction.UPDATED,
                    "delete": InstagramCommentAction.DELETED,
                    "remove": InstagramCommentAction.DELETED
                }
                action = action_map.get(verb.lower(), InstagramCommentAction.CREATED)

                author_id = None
                from_data = value.get("from") or value.get("user") or {}
                if isinstance(from_data, dict):
                    author_id = from_data.get("id")

                mentioned_user_id = None
                to_data = value.get("to") or {}
                if isinstance(to_data, dict):
                    mentioned_user_id = to_data.get("id")

                text = value.get("text") or value.get("message")
                hidden = bool(value.get("hidden", False))
                raw_ts = value.get("timestamp") or value.get("created_time") or int(utc_now().timestamp() * 1000)
                if raw_ts > 10**12:
                    timestamp_seconds = int(raw_ts / 1000)
                else:
                    timestamp_seconds = int(raw_ts)
                comment_ts = timestamp_seconds

                comment_record = upsert_instagram_comment(
                    db=db,
                    comment_id=comment_id,
                    media_id=media_id,
                    author_id=author_id,
                    text=text,
                    hidden=hidden,
                    action=action,
                    mentioned_user_id=mentioned_user_id,
                    ts=comment_ts,
                    attachments=None
                )
                db.commit()
                db.refresh(comment_record)

                comment_payload = {
                    "type": "ig_comment",
                    "action": comment_record.action.value,
                    "media_id": comment_record.media_id,
                    "comment_id": comment_record.id,
                    "text": comment_record.text,
                    "author_id": comment_record.author_id,
                    "hidden": comment_record.hidden,
                    "timestamp": comment_record.ts,
                    "mentioned_user_id": comment_record.mentioned_user_id
                }

                await ws_manager.broadcast_global(comment_payload)
                processed_events += 1

        return {"status": "received", "processed_events": processed_events}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error processing Instagram webhook: {exc}", exc_info=True)
        # Return 200 to avoid Facebook retrying
        return {"status": "error", "message": str(exc)}

@api_router.post("/webhooks/instagram")
async def handle_instagram_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Instagram webhook"""
    return await _handle_instagram_webhook(request, db)

@app.post("/webhook")
async def instagram_dm_webhook(request: Request, db: Session = Depends(get_db)):
    """Unified webhook entrypoint for Meta subscriptions."""
    return await _handle_instagram_webhook(request, db)

@app.post("/messages/send")
@app.post("/send", include_in_schema=False)
async def instagram_dm_send(
    payload: InstagramSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send an Instagram DM via the Meta Graph API."""
    page_id = INSTAGRAM_PAGE_ID

    chat = db.query(Chat).filter(
        Chat.instagram_user_id == payload.igsid,
        Chat.platform == MessagePlatform.INSTAGRAM
    ).first()

    if chat and chat.facebook_page_id:
        page_id = chat.facebook_page_id

    if not page_id:
        raise HTTPException(status_code=400, detail="Instagram page ID not configured")

    page_access_token = resolve_instagram_access_token(db, page_id)
    if not page_access_token:
        raise HTTPException(status_code=500, detail="Instagram page access token missing")

    send_result = await instagram_client.send_dm(
        page_id=page_id,
        page_access_token=page_access_token,
        recipient_id=payload.igsid,
        text=payload.text if payload.has_text else None,
        attachments=payload.attachments
    )

    if not send_result.get("success"):
        error_message = send_result.get("error", "Failed to send message")
        logger.error(f"Failed to send Instagram DM to {payload.igsid}: {error_message}")
        raise HTTPException(status_code=502, detail=error_message)

    graph_message_id = send_result.get("message_id")
    normalized_graph_message_id = graph_message_id[:255] if graph_message_id else None
    now_utc = utc_now()
    timestamp_seconds = int(now_utc.timestamp())
    attachments_json = json.dumps(payload.attachments) if payload.attachments else None
    message_content = resolve_message_text(payload.text, payload.attachments or []) or ""
    last_message_preview = message_content or None

    profile_username = None
    profile_name = None
    if chat:
        if chat.instagram_user:
            profile_username = chat.instagram_user.username or chat.username
            profile_name = chat.instagram_user.name or chat.username
        else:
            profile_username = chat.username
            profile_name = chat.username

    instagram_user = ensure_instagram_user(
        db=db,
        igsid=payload.igsid,
        event_datetime=now_utc,
        last_message_preview=last_message_preview,
        profile_username=profile_username,
        profile_name=profile_name
    )

    outbound_message = InstagramMessageLog(
        igsid=payload.igsid,
        message_id=normalized_graph_message_id,
        direction=InstagramMessageDirection.OUTBOUND,
        text=payload.text,
        attachments_json=attachments_json,
        ts=timestamp_seconds,
        created_at=now_utc,
        raw_payload_json=json.dumps({
            "text": payload.text,
            "attachments": payload.attachments or [],
            "graph_message_id": graph_message_id
        }),
        is_ticklegram=True
    )
    db.add(outbound_message)

    if not chat:
        profile = await instagram_client.get_user_profile(
            page_access_token=page_access_token,
            user_id=payload.igsid
        )
        username = profile.get("username") or profile.get("name") or f"IG User {payload.igsid[:8]}"
        profile_pic_url = profile.get("profile_pic_url") or profile.get("profile_pic")
        if not profile_pic_url:
            profile_pic_url = f"https://via.placeholder.com/150?text={payload.igsid[:8]}"

        instagram_user.username = profile.get("username") or instagram_user.username
        instagram_user.name = profile.get("name") or instagram_user.name

        chat = Chat(
            instagram_user_id=payload.igsid,
            username=username,
            profile_pic_url=profile_pic_url,
            platform=MessagePlatform.INSTAGRAM,
            facebook_page_id=page_id,
            status=ChatStatus.UNASSIGNED
        )
        db.add(chat)
        db.flush()
    else:
        if not chat.facebook_page_id:
            chat.facebook_page_id = page_id

    if last_message_preview:
        chat.last_message = last_message_preview
    chat.last_outgoing_at = now_utc
    chat.updated_at = now_utc

    message_record = create_chat_message_record(
        chat,
        sender=MessageSender.AGENT,
        content=message_content,
        message_type=MessageType.TEXT,
        timestamp=now_utc,
        is_ticklegram=True,
        attachments_json=attachments_json,
        metadata_json=_merge_message_metadata(None, sent_by=current_user)
    )
    message_record.attachments = payload.attachments or []
    db.add(message_record)

    db.flush()
    db.commit()

    db.refresh(outbound_message)
    db.refresh(message_record)
    db.refresh(chat)

    notify_users = gather_dm_notify_users(db, chat)

    # Broadcast chat message event
    if notify_users:
        message_payload = MessageResponse.model_validate(message_record).model_dump(mode="json")
        await ws_manager.broadcast_to_users(notify_users, {
            "type": "new_message",
            "chat_id": str(chat.id),
            "platform": chat.platform.value,
            "sender": MessageSender.AGENT.value,
            "message": message_payload
        })

        dm_payload = {
            "type": "ig_dm",
            "legacy_type": "instagram_dm",
            "direction": InstagramMessageDirection.OUTBOUND.value,
            "igsid": payload.igsid,
            "text": payload.text,
            "attachments": payload.attachments or [],
            "timestamp": timestamp_seconds,
            "message_id": outbound_message.id,
            "graph_message_id": graph_message_id,
            "page_id": page_id,
            "delivery_status": "sent",
            "sent_by": str(current_user.id)
        }
        await ws_manager.broadcast_to_users(notify_users, dm_payload)

    logger.info(f"Instagram DM sent to {payload.igsid} by user {current_user.id}")
    return {
        "success": True,
        "message_id": outbound_message.id,
        "graph_message_id": graph_message_id,
        "timestamp": timestamp_seconds,
        "igsid": payload.igsid
    }

# ============= CHAT ENDPOINTS =============

@api_router.get("/chats", response_model=List[ChatResponse])
def list_chats(
    status_filter: Optional[str] = None,
    assigned_to_me: bool = False,
    platform: Optional[str] = None,
    assigned_to: Optional[str] = None,
    unseen: Optional[bool] = None,
    not_replied: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Chat).options(
        joinedload(Chat.assigned_agent),
        joinedload(Chat.instagram_user),
        joinedload(Chat.facebook_user)
    )
    
    # Filter by status
    if status_filter:
        if status_filter == "assigned":
            query = query.filter(Chat.status == ChatStatus.ASSIGNED)
        elif status_filter == "unassigned":
            query = query.filter(Chat.status == ChatStatus.UNASSIGNED)
    
    # Filter by platform
    if platform:
        if platform.upper() == "INSTAGRAM":
            query = query.filter(Chat.platform == MessagePlatform.INSTAGRAM)
        elif platform.upper() == "FACEBOOK":
            query = query.filter(Chat.platform == MessagePlatform.FACEBOOK)
    
    if assigned_to and assigned_to.lower() == "unassigned":
        query = query.filter(Chat.assigned_to.is_(None))
    elif assigned_to:
        query = query.filter(Chat.assigned_to == assigned_to)

    if unseen is True:
        query = query.filter(Chat.unread_count > 0)
    elif unseen is False:
        query = query.filter(Chat.unread_count == 0)

    if not_replied is True:
        query = query.filter(Chat.last_incoming_at.isnot(None)).filter(
            or_(Chat.last_outgoing_at.is_(None), Chat.last_outgoing_at < Chat.last_incoming_at)
        )
    elif not_replied is False:
        query = query.filter(
            or_(
                Chat.last_incoming_at.is_(None),
                Chat.last_outgoing_at.isnot(None),
                Chat.last_outgoing_at >= Chat.last_incoming_at,
            )
        )
    
    # Filter by assigned to current user (for agents without wider visibility)
    if assigned_to_me or not _user_can_view_all_chats(current_user):
        query = query.filter(Chat.assigned_to == current_user.id)
    
    chats = query.order_by(Chat.updated_at.desc()).all()

    missing_instagram_ids = {
        chat.instagram_user_id
        for chat in chats
        if chat.platform == MessagePlatform.INSTAGRAM
        and chat.instagram_user_id
        and chat.instagram_user is None
    }
    if missing_instagram_ids:
        instagram_map = {
            user.igsid: user
            for user in db.query(InstagramUser).filter(InstagramUser.igsid.in_(missing_instagram_ids)).all()
        }
        for chat in chats:
            if chat.platform == MessagePlatform.INSTAGRAM and not chat.instagram_user:
                resolved = instagram_map.get(chat.instagram_user_id)
                if resolved:
                    chat.instagram_user = resolved

    missing_facebook_ids = {
        chat.facebook_user_id
        for chat in chats
        if chat.platform == MessagePlatform.FACEBOOK
        and chat.facebook_user_id
        and chat.facebook_user is None
    }
    if missing_facebook_ids:
        facebook_map = {
            user.id: user
            for user in db.query(FacebookUser).filter(FacebookUser.id.in_(missing_facebook_ids)).all()
        }
        for chat in chats:
            if chat.platform == MessagePlatform.FACEBOOK and not chat.facebook_user:
                resolved = facebook_map.get(chat.facebook_user_id)
                if resolved:
                    chat.facebook_user = resolved

    for chat in chats:
        chat.pending_agent_reply = _chat_requires_agent_reply(chat)

    return chats

@api_router.get("/chats/{chat_id}", response_model=ChatWithMessages)
def get_chat(chat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = (
        db.query(Chat)
        .options(
            joinedload(Chat.instagram_chat_messages),
            joinedload(Chat.facebook_chat_messages),
            joinedload(Chat.assigned_agent),
            joinedload(Chat.instagram_user),
            joinedload(Chat.facebook_user),
        )
        .filter(Chat.id == chat_id)
        .first()
    )
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    _assert_chat_access(current_user, chat)
    
    # Mark messages as read by resetting unread count
    chat.unread_count = 0
    db.commit()

    for msg in chat.messages or []:
        normalize_message_sender(msg)

    instagram_msgs: List[InstagramMessageLog] = []
    if chat.platform == MessagePlatform.INSTAGRAM:
        instagram_msgs = db.query(InstagramMessageLog).filter(
            InstagramMessageLog.igsid == chat.instagram_user_id
        ).all()
    hydrate_instagram_chat_messages(chat, instagram_msgs)
    chat.pending_agent_reply = _chat_requires_agent_reply(chat)
    return chat

@api_router.post("/chats/{chat_id}/assign")
def assign_chat(
    chat_id: str,
    assignment: ChatAssign,
    current_user: User = Depends(require_permissions(PermissionCode.CHAT_ASSIGN)),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if assignment.agent_id:
        agent = (
            db.query(User)
            .options(joinedload(User.position))
            .filter(User.id == assignment.agent_id, User.role == UserRole.AGENT)
            .first()
        )
        if not agent or not _is_assignable_agent(agent):
            raise HTTPException(status_code=404, detail="Agent not found")
        chat.assigned_to = assignment.agent_id
        chat.status = ChatStatus.ASSIGNED
    else:
        chat.assigned_to = None
        chat.status = ChatStatus.UNASSIGNED
    
    db.commit()
    db.refresh(chat)
    
    logger.info(f"Chat {chat_id} assigned to {assignment.agent_id or 'unassigned'}")
    return {"success": True, "chat": ChatResponse.model_validate(chat)}

@api_router.post("/chats/{chat_id}/mark_read")
def mark_chat_as_read(chat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a chat as read by resetting unread count"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    _assert_chat_access(current_user, chat)
    
    # Reset unread count
    chat.unread_count = 0
    db.commit()
    
    logger.info(f"Chat {chat_id} marked as read by user {current_user.id}")
    return {"success": True, "chat_id": chat_id}

@api_router.post("/chats/{chat_id}/message", response_model=MessageResponse)
async def send_message(chat_id: str, message_data: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    _assert_chat_access(current_user, chat)
    
    # Enforce Meta's 24-hour human agent policy (Facebook only)
    if chat.platform == MessagePlatform.FACEBOOK:
        message_model = _message_model_for_platform(chat.platform)
        last_customer_message = (
            message_query_for_chat(db, chat)
            .filter(
                message_model.chat_id == chat_id,
                message_model.sender != MessageSender.AGENT
            )
            .order_by(message_model.timestamp.desc())
            .first()
        )

        if last_customer_message:
            # Ensure the timestamp is timezone-aware before comparison
            msg_timestamp = last_customer_message.timestamp
            if not msg_timestamp.tzinfo:
                msg_timestamp = msg_timestamp.replace(tzinfo=timezone.utc)
            window_deadline = msg_timestamp + timedelta(hours=24)
            if utc_now() > window_deadline:
                raise HTTPException(
                    status_code=403,
                    detail="Outside the 24-hour human agent window. Send an approved template instead."
                )

    attachments_payload = message_data.attachments or []
    message_content = (message_data.content or "").strip()
    if not message_content and not attachments_payload:
        raise HTTPException(status_code=400, detail="Message content or attachment required")
    if not message_content:
        message_content = "[attachment]"

    reply_metadata: Dict[str, Any] = {}
    if message_data.reply_to_message_id:
        reply_metadata = _build_reply_metadata(
            db=db,
            chat=chat,
            reply_message_id=message_data.reply_to_message_id,
            reply_preview=message_data.reply_preview
        )

    event_time = utc_now()

    # If in mock mode, just create the message without actual platform integration
    if instagram_client.mode == InstagramMode.MOCK and facebook_client.mode == FacebookMode.MOCK:
        new_message = create_chat_message_record(
            chat,
            sender=MessageSender.AGENT,
            content=message_content,
            message_type=message_data.message_type,
            timestamp=event_time,
            is_ticklegram=True,
            metadata_json=_merge_message_metadata(
                None,
                sent_by=current_user,
                extra=reply_metadata or None
            )
        )
        new_message.attachments = attachments_payload
        db.add(new_message)
        chat.last_message = message_content
        chat.last_outgoing_at = event_time
        chat.updated_at = event_time
        db.commit()
        db.refresh(new_message)
        logger.info(f"Mock message sent in chat {chat_id}")
        return new_message
    
    # For real mode, send through appropriate platform
    if chat.platform == MessagePlatform.FACEBOOK:
        if not chat.facebook_user_id:
            raise HTTPException(status_code=400, detail="Facebook user reference missing for this chat")
        # Get Facebook page access token
        if chat.facebook_page_id:
            fb_page = db.query(FacebookPage).filter(FacebookPage.page_id == chat.facebook_page_id).first()
            if fb_page and fb_page.is_active:
                reply_mid = reply_metadata.get("reply_facebook_mid")
                if attachments_payload:
                    for attachment in attachments_payload:
                        att_type = (attachment.get("type") or "").lower()
                        payload = attachment.get("payload") or {}
                        url = payload.get("url") or attachment.get("url")
                        if not att_type or not url:
                            continue
                        result = await facebook_client.send_attachment(
                            page_access_token=fb_page.access_token,
                            recipient_id=chat.facebook_user_id,
                            attachment_type=att_type,
                            attachment_url=url
                        )
                        if not result.get("success"):
                            logger.error(f"Failed to send Facebook attachment: {result.get('error')}")
                            raise HTTPException(status_code=500, detail=f"Failed to send attachment: {result.get('error')}")
                else:
                    result = await facebook_client.send_text_message(
                        page_access_token=fb_page.access_token,
                        recipient_id=chat.facebook_user_id,
                        text=message_content,
                        reply_to_mid=reply_mid
                    )
                    if not result.get("success"):
                        logger.error(f"Failed to send Facebook message: {result.get('error')}")
                        raise HTTPException(status_code=500, detail=f"Failed to send message: {result.get('error')}")
            else:
                raise HTTPException(status_code=400, detail="Facebook page not found or inactive")
        else:
            raise HTTPException(status_code=400, detail="No Facebook page associated with this chat")
    
    elif chat.platform == MessagePlatform.INSTAGRAM:
        # Get Instagram account access token
        if chat.facebook_page_id:  # This stores the Instagram account ID
            ig_account = db.query(InstagramAccount).filter(InstagramAccount.page_id == chat.facebook_page_id).first()
            if ig_account:
                # Send via Instagram
                result = await instagram_client.send_text_message(
                    page_access_token=ig_account.access_token,
                    recipient_id=chat.instagram_user_id,
                    text=message_content
                )
                if not result.get("success"):
                    logger.error(f"Failed to send Instagram message: {result.get('error')}")
                    raise HTTPException(status_code=500, detail=f"Failed to send message: {result.get('error')}")
            else:
                raise HTTPException(status_code=400, detail="Instagram account not found")
        else:
            raise HTTPException(status_code=400, detail="No Instagram account associated with this chat")
    
    # Create message record in database
    new_message = create_chat_message_record(
        chat,
        sender=MessageSender.AGENT,
        content=message_content,
        message_type=message_data.message_type,
        timestamp=event_time,
        is_ticklegram=True,
        attachments_json=_dump_attachments_json(attachments_payload),
        metadata_json=_merge_message_metadata(
            None,
            sent_by=current_user,
            extra=reply_metadata or None
        )
    )
    new_message.attachments = attachments_payload
    db.add(new_message)
    
    # Update chat
    chat.last_message = message_content
    chat.last_outgoing_at = event_time
    chat.updated_at = event_time
    
    db.commit()
    db.refresh(new_message)
    
    message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")

    # Notify relevant users about the sent message
    notify_users = set()
    
    # Add assigned agent if any
    if chat.assigned_to:
        notify_users.add(str(chat.assigned_to))
    
    # Add admin users
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    notify_users.update(str(user.id) for user in admin_users)
    
    # Broadcast message sent notification
    await ws_manager.broadcast_to_users(notify_users, {
        "type": "new_message",
        "chat_id": str(chat.id),
        "platform": chat.platform.value,
        "sender": "agent",
        "message": message_payload
    })
    
    logger.info(f"Message sent in chat {chat_id} by {current_user.email} on {chat.platform}")
    return new_message

# ============= DASHBOARD ENDPOINTS =============

@api_router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == UserRole.ADMIN:
        total_chats = db.query(Chat).count()
        assigned_chats = db.query(Chat).filter(Chat.status == ChatStatus.ASSIGNED).count()
        unassigned_chats = db.query(Chat).filter(Chat.status == ChatStatus.UNASSIGNED).count()
        instagram_chats = db.query(Chat).filter(Chat.platform == MessagePlatform.INSTAGRAM).count()
        facebook_chats = db.query(Chat).filter(Chat.platform == MessagePlatform.FACEBOOK).count()
    else:
        # Agents only see their stats
        total_chats = db.query(Chat).filter(Chat.assigned_to == current_user.id).count()
        assigned_chats = total_chats
        unassigned_chats = 0
        instagram_chats = db.query(Chat).filter(
            Chat.assigned_to == current_user.id,
            Chat.platform == MessagePlatform.INSTAGRAM
        ).count()
        facebook_chats = db.query(Chat).filter(
            Chat.assigned_to == current_user.id,
            Chat.platform == MessagePlatform.FACEBOOK
        ).count()
    
    total_messages = db.query(InstagramChatMessage).count() + db.query(FacebookMessage).count()
    active_agents = len(_get_assignable_agents(db))
    
    return DashboardStats(
        total_chats=total_chats,
        assigned_chats=assigned_chats,
        unassigned_chats=unassigned_chats,
        total_messages=total_messages,
        active_agents=active_agents,
        instagram_chats=instagram_chats,
        facebook_chats=facebook_chats
    )

# ============= FACEBOOK ENDPOINTS =============

@api_router.post("/facebook/pages", response_model=FacebookPageResponse)
def connect_facebook_page(
    page_data: FacebookPageConnect,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Connect a Facebook page"""
    # Check if page already exists
    existing_page = db.query(FacebookPage).filter(FacebookPage.page_id == page_data.page_id).first()
    if existing_page:
        # Update existing page
        existing_page.page_name = page_data.page_name or existing_page.page_name
        existing_page.access_token = page_data.access_token
        existing_page.is_active = True
        existing_page.updated_at = utc_now()
        db.commit()
        db.refresh(existing_page)
        logger.info(f"Updated Facebook page: {page_data.page_id}")
        return existing_page
    
    # Create new Facebook page
    new_page = FacebookPage(
        user_id=current_user.id,
        page_id=page_data.page_id,
        page_name=page_data.page_name or f"Facebook Page {page_data.page_id[:8]}",
        access_token=page_data.access_token
    )
    db.add(new_page)
    db.commit()
    db.refresh(new_page)
    
    logger.info(f"Connected Facebook page: {page_data.page_id}")
    return new_page

@api_router.get("/facebook/pages", response_model=List[FacebookPageResponse])
def list_facebook_pages(
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """List all connected Facebook pages"""
    pages = db.query(FacebookPage).all()
    return pages

@api_router.get("/facebook/pages/{page_id}", response_model=FacebookPageResponse)
def get_facebook_page(
    page_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Get a specific Facebook page"""
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Facebook page not found")
    return page

@api_router.patch("/facebook/pages/{page_id}", response_model=FacebookPageResponse)
def update_facebook_page(
    page_id: str,
    page_update: FacebookPageUpdate,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Update a Facebook page"""
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Facebook page not found")

    old_status = page.is_active

    if page_update.page_name is not None:
        page.page_name = page_update.page_name
    if page_update.access_token is not None:
        page.access_token = page_update.access_token
    if page_update.is_active is not None:
        page.is_active = page_update.is_active
    
    page.updated_at = utc_now()
    db.commit()
    db.refresh(page)

    # Persist status change log
    if page_update.is_active is not None and old_status != page_update.is_active:
        try:
            log_entry = FacebookPageStatusLog(
                page_id=page.page_id,
                changed_by=current_user.email or current_user.id,
                changed_to=page_update.is_active,
                note=f"Status changed from {old_status} to {page_update.is_active}",
            )
            db.add(log_entry)
            db.commit()
        except Exception as exc:
            logger.error("Failed to log page status change: %s", exc)

    logger.info(
        "Updated Facebook page %s is_active=%s by user=%s (%s)",
        page_id,
        page.is_active,
        current_user.id,
        current_user.email or current_user.name,
    )
    return page

@api_router.delete("/facebook/pages/{page_id}")
def delete_facebook_page(
    page_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Delete a Facebook page"""
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Facebook page not found")
    
    db.delete(page)
    db.commit()
    
    logger.info(f"Deleted Facebook page: {page_id}")
    return {"success": True, "message": "Facebook page deleted"}

# Template Endpoints
@api_router.get("/templates", response_model=List[MessageTemplateResponse])
def list_templates(
    platform: Optional[MessagePlatform] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all templates with optional filtering by platform and category"""
    query = db.query(MessageTemplate)
    
    if platform:
        query = query.filter(MessageTemplate.platform == platform)
    if category:
        query = query.filter(MessageTemplate.category == category)
    
    templates = query.order_by(MessageTemplate.created_at.desc()).all()
    return templates

@api_router.post("/templates", response_model=MessageTemplateResponse)
def create_template(
    template_data: MessageTemplateCreate,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Create a new template (admin only)"""
    if template_data.is_meta_approved and not template_data.meta_template_id:
        raise HTTPException(
            status_code=400,
            detail="Meta-approved templates must include a Meta template ID"
        )

    new_template = MessageTemplate(
        name=template_data.name,
        content=template_data.content,
        category=template_data.category,
        platform=template_data.platform,
        meta_template_id=template_data.meta_template_id,
        is_meta_approved=template_data.is_meta_approved,
        created_by=current_user.id
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    logger.info(f"Template created: {new_template.id} by user {current_user.email}")
    return new_template

@api_router.put("/templates/{template_id}", response_model=MessageTemplateResponse)
def update_template(
    template_id: str,
    template_data: MessageTemplateUpdate,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Update a template (admin only)"""
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Only allow updating basic template info
    if hasattr(template_data, 'name') and template_data.name is not None:
        template.name = template_data.name
    if hasattr(template_data, 'content') and template_data.content is not None:
        template.content = template_data.content
    if hasattr(template_data, 'category') and template_data.category is not None:
        template.category = template_data.category
    if hasattr(template_data, 'platform') and template_data.platform is not None:
        template.platform = template_data.platform
        
    # Don't allow manual updates of Meta approval status
    if (
        template_data.is_meta_approved is not None
        or template_data.meta_template_id is not None
        or template_data.meta_submission_id is not None
        or template_data.meta_submission_status is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Meta approval status and template ID can only be updated through the Meta approval process"
        )

    template.updated_at = utc_now()
    db.commit()
    db.refresh(template)
    
    logger.info(f"Template updated: {template_id} by user {current_user.email}")
    return template

@api_router.post("/templates/{template_id}/submit-to-meta")
async def submit_template_to_meta(
    template_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Submit a template for Meta's approval"""
    from meta_template_api import meta_template_api
    
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.meta_submission_status == "pending":
        raise HTTPException(status_code=400, detail="Template is already pending Meta approval")

    entity_id, entity_token = resolve_meta_entity_for_template(db, template, current_user)

    try:
        # Log template info for debugging
        logger.info(
            "Submitting template %s via Meta entity %s (platform=%s, category=%s)",
            template_id,
            entity_id,
            template.platform,
            template.category,
        )
        
        # Validate and normalize category for Meta API
        category_map = {
            'CUSTOMER_SUPPORT': 'UTILITY',
            'SUPPORT': 'UTILITY',
            'UTILITY': 'UTILITY',
            'GREETING': 'UTILITY',
            'CLOSING': 'UTILITY',
            'MARKETING': 'MARKETING',
            'PROMOTION': 'MARKETING',
            'SALES': 'MARKETING',
            'AUTHENTICATION': 'AUTHENTICATION',
            'OTP': 'AUTHENTICATION',
            'SECURITY': 'AUTHENTICATION',
        }
        category_key = (template.category or '').upper()
        meta_category = category_map.get(category_key)
        if not meta_category:
            valid_labels = ['Utility', 'Marketing', 'Authentication']
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported template category '{template.category}'. Please select one of: {', '.join(valid_labels)}"
            )
        
        # Prepare template data
        template_data = {
            "name": template.name,
            "category": meta_category,
            "content": template.content,
            "platform": template.platform
        }
        
        # Submit to Meta
        result = await meta_template_api.submit_template(entity_id, template_data, entity_token)
        
        # Update template with submission info
        template.meta_submission_id = result['id']
        template.meta_submission_status = result['status']
        template.updated_at = utc_now()
        
        try:
            db.commit()
        except Exception as db_error:
            logger.error(f"Database error while updating template status: {db_error}")
            raise HTTPException(
                status_code=500,
                detail="Template was submitted but failed to update status in database"
            )
        
        return {
            "message": "Template submitted for Meta approval",
            "status": result['status'],
            "meta_submission_id": result['id']
        }
        
    except HTTPException as http_error:
        # Re-raise HTTP exceptions with their original status codes
        raise http_error
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to submit template to Meta: {error_msg}")
        # Include more details in the error message
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit template to Meta: {error_msg}"
        )

@api_router.delete("/templates/{template_id}")
def delete_template(
    template_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Delete a template (admin only)"""
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    logger.info(f"Template deleted: {template_id} by user {current_user.email}")
    return {"success": True, "message": "Template deleted"}

@api_router.get("/templates/{template_id}/meta-status")
async def check_meta_template_status(
    template_id: str,
    current_user: User = Depends(get_admin_only_user),
    db: Session = Depends(get_db)
):
    """Check the Meta approval status of a template"""
    from meta_template_api import meta_template_api
    
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template.meta_submission_id:
        raise HTTPException(status_code=400, detail="Template has not been submitted to Meta")

    try:
        # Check template status with Meta
        entity_id, entity_token = resolve_meta_entity_for_template(db, template, current_user)

        result = await meta_template_api.check_template_status(
            entity_id, template.meta_submission_id, entity_token
        )
        
        # Update template status in database
        old_status = template.meta_submission_status
        template.meta_submission_status = result['status']
        
        # If status changed to approved, update template
        if result['status'] == 'approved' and old_status != 'approved':
            template.is_meta_approved = True
            template.meta_template_id = result.get('template_id')  # Meta may provide a permanent template ID
            
        template.updated_at = utc_now()
        db.commit()
        
        return {
            "message": "Template status retrieved successfully",
            "status": result['status'],
            "template_id": template.meta_template_id
        }
    except Exception as e:
        logger.error(f"Failed to check template status with Meta: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check template status. Please try again later."
        )

@api_router.post("/templates/{template_id}/send", response_model=MessageResponse)
async def send_template(
    template_id: str,
    send_request: TemplateSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a template message to a chat"""
    # Get template
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get chat
    chat = db.query(Chat).filter(Chat.id == send_request.chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    _assert_chat_access(current_user, chat)
    
    # Check platform match
    if template.platform != chat.platform:
        raise HTTPException(status_code=400, detail=f"Template platform ({template.platform}) doesn't match chat platform ({chat.platform})")
    
    # Enforce Meta's 24-hour policy for template sending
    message_model = _message_model_for_platform(chat.platform)
    last_customer_message = (
        message_query_for_chat(db, chat)
        .filter(
            message_model.chat_id == chat.id,
            message_model.sender != MessageSender.AGENT
        )
        .order_by(message_model.timestamp.desc())
        .first()
    )

    # Always allow template messages for now during testing
    # Comment out the 24-hour window check temporarily
    """
    if last_customer_message:
        window_deadline = last_customer_message.timestamp + timedelta(hours=24)
        if utc_now() > window_deadline and not template.is_meta_approved:
            raise HTTPException(
                status_code=403,
                detail="Outside the 24-hour human agent window. Only Meta-approved templates can be sent."
            )
    """

    # Perform variable substitution
    message_content = template.content
    if send_request.variables:
        for key, value in send_request.variables.items():
            placeholder = f"{{{key}}}"
            message_content = message_content.replace(placeholder, str(value))
    
    # Auto-populate common variables from chat context
    username_value = None
    if chat.platform == MessagePlatform.INSTAGRAM and chat.instagram_user:
        username_value = chat.instagram_user.name or chat.instagram_user.username
    if chat.platform == MessagePlatform.FACEBOOK and chat.facebook_user:
        username_value = chat.facebook_user.name or chat.facebook_user.username
    username_value = username_value or chat.username or chat.instagram_user_id or chat.facebook_user_id or ""
    message_content = message_content.replace("{username}", username_value)
    message_content = message_content.replace("{platform}", chat.platform.value)
    
    reply_metadata: Dict[str, Any] = {}
    if send_request.reply_to_message_id:
        reply_metadata = _build_reply_metadata(
            db=db,
            chat=chat,
            reply_message_id=send_request.reply_to_message_id,
            reply_preview=send_request.reply_preview
        )

    meta_template_tag = os.getenv("META_TEMPLATE_TAG", "ACCOUNT_UPDATE")
    use_meta_template = template.is_meta_approved
    event_time = utc_now()

    if use_meta_template and not template.meta_template_id:
        raise HTTPException(
            status_code=400,
            detail="Meta-approved template is missing the Meta template ID"
        )
    
    if instagram_client.mode == InstagramMode.MOCK and facebook_client.mode == FacebookMode.MOCK:
        new_message = create_chat_message_record(
            chat,
            sender=MessageSender.AGENT,
            content=message_content,
            message_type=MessageType.TEXT,
            timestamp=event_time,
            is_ticklegram=True,
            metadata_json=_merge_message_metadata(
                None,
                sent_by=current_user,
                extra=reply_metadata or None
            )
        )
        new_message.attachments = []
        db.add(new_message)
        chat.last_message = message_content
        chat.last_outgoing_at = event_time
        chat.updated_at = event_time
        db.commit()
        db.refresh(new_message)
        logger.info(f"Template message sent (mock mode) in chat {chat.id}")
    else:
        # Send through appropriate platform
        if chat.platform == MessagePlatform.FACEBOOK:
            if not chat.facebook_user_id:
                raise HTTPException(status_code=400, detail="Facebook user reference missing for this chat")
            if chat.facebook_page_id:
                fb_page = db.query(FacebookPage).filter(FacebookPage.page_id == chat.facebook_page_id).first()
                if fb_page and fb_page.is_active:
                    if use_meta_template:
                        result = await facebook_client.send_template_message(
                            page_access_token=fb_page.access_token,
                            recipient_id=chat.facebook_user_id,
                            text=message_content,
                            template_id=template.meta_template_id,
                            tag=meta_template_tag,
                            reply_to_mid=reply_metadata.get("reply_facebook_mid")
                        )
                    else:
                        result = await facebook_client.send_text_message(
                            page_access_token=fb_page.access_token,
                            recipient_id=chat.facebook_user_id,
                            text=message_content,
                            reply_to_mid=reply_metadata.get("reply_facebook_mid")
                        )
                    if not result.get("success"):
                        raise HTTPException(status_code=500, detail=f"Failed to send message: {result.get('error')}")
                else:
                    raise HTTPException(status_code=400, detail="Facebook page not found or inactive")
            else:
                raise HTTPException(status_code=400, detail="No Facebook page associated with this chat")
        
        elif chat.platform == MessagePlatform.INSTAGRAM:
            if chat.facebook_page_id:
                ig_account = db.query(InstagramAccount).filter(InstagramAccount.page_id == chat.facebook_page_id).first()
                if ig_account:
                    if use_meta_template:
                        result = await instagram_client.send_template_message(
                            page_access_token=ig_account.access_token,
                            recipient_id=chat.instagram_user_id,
                            text=message_content,
                            template_id=template.meta_template_id,
                            tag=meta_template_tag
                        )
                    else:
                        result = await instagram_client.send_text_message(
                            page_access_token=ig_account.access_token,
                            recipient_id=chat.instagram_user_id,
                            text=message_content
                        )
                    if not result.get("success"):
                        raise HTTPException(status_code=500, detail=f"Failed to send message: {result.get('error')}")
                else:
                    raise HTTPException(status_code=400, detail="Instagram account not found")
            else:
                raise HTTPException(status_code=400, detail="No Instagram account associated with this chat")
        
    new_message = create_chat_message_record(
        chat,
        sender=MessageSender.AGENT,
        content=message_content,
        message_type=MessageType.TEXT,
        timestamp=event_time,
        is_ticklegram=True,
        metadata_json=_merge_message_metadata(
            None,
            sent_by=current_user,
            extra=reply_metadata or None
        )
    )
        # new_message.attachments = []
        # db.add(new_message)
        # chat.last_message = message_content
        # chat.last_outgoing_at = event_time
        # chat.updated_at = event_time
        # db.commit()
        # db.refresh(new_message)
    
    # Broadcast via WebSocket
    message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")
    notify_users = set()
    if chat.assigned_to:
        notify_users.add(str(chat.assigned_to))
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    notify_users.update(str(user.id) for user in admin_users)
    
    await ws_manager.broadcast_to_users(notify_users, {
        "type": "new_message",
        "chat_id": chat.id,
        "message": message_payload
    })
    
    logger.info(f"Template {template_id} sent to chat {chat.id}")
    return new_message

# Facebook Webhook Endpoints
@api_router.get("/webhooks/facebook")
async def verify_facebook_webhook(
    request: Request,
    hub_mode: str = Query("", alias="hub.mode"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    hub_verify_token: str = Query("", alias="hub.verify_token")
):
    
    if facebook_client.verify_webhook_token(hub_mode, hub_verify_token):
        logger.info("Facebook webhook verification successful")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    else:
        logger.warning("Facebook webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@api_router.post("/webhooks/facebook")
async def handle_facebook_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Facebook webhook"""
    try:
        # Get raw body for signature verification
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Hub-Signature", "")
        
        # Verify signature (skip in mock mode)
        if not facebook_client.verify_webhook_signature(body, signature):
            logger.warning("Invalid Facebook webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        data = await request.json()
        logger.info(f"Received Facebook webhook: {data.get('object')}")
        event_entry = data.get("entry", [])
        first_entry = event_entry[0] if isinstance(event_entry, list) and event_entry else {}
        event_page_id = first_entry.get("id") if isinstance(first_entry, dict) else None
        webhook_event = FacebookWebhookEvent(
            object=data.get("object"),
            page_id=event_page_id,
            payload=data
        )
        db.add(webhook_event)
        db.flush()
        processed_messaging_event = False
        
        # Process webhook entries
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                page_id = entry.get("id")
                if not webhook_event.page_id and page_id:
                    webhook_event.page_id = page_id
                
                # Get Facebook page from database
                fb_page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
                if not fb_page:
                    logger.warning(f"Received webhook for unknown page: {page_id}")
                    continue
                
                # Process messaging events
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event.get("sender", {}).get("id")
                    recipient_id = messaging_event.get("recipient", {}).get("id")
                    
                    # Handle message
                    if "message" in messaging_event:
                        message_data = messaging_event["message"]
                        
                        # Process message
                        processed = await facebook_client.process_webhook_message(
                            sender_id=sender_id,
                            recipient_id=recipient_id,
                            message_data=message_data,
                            page_id=page_id
                        )
                        fb_attachments = processed.get("attachments") or []
                        if _is_useless_template_attachments(fb_attachments) and not (processed.get("text") or "").strip():
                            logger.info(
                                "Skipping template-only Facebook webhook message sender=%s page=%s",
                                sender_id,
                                page_id,
                            )
                            continue
                        fb_referral_payload = _normalize_referral_payload(
                            _extract_messaging_referral(messaging_event)
                        )
                        fb_extra_meta: Dict[str, Any] = {}
                        if fb_referral_payload:
                            fb_extra_meta["referral"] = fb_referral_payload
                        if processed.get("message_id"):
                            fb_extra_meta["facebook_mid"] = processed.get("message_id")
                        # include full raw webhook payload
                        fb_extra_meta["raw_webhook"] = messaging_event
                        fb_metadata_json = _merge_message_metadata(
                            None,
                            extra=fb_extra_meta or None
                        )

                        lead_form = is_lead_form_message(processed.get("text"))

                        chat = db.query(Chat).filter(
                            Chat.facebook_user_id == sender_id,
                            Chat.platform == MessagePlatform.FACEBOOK,
                            Chat.facebook_page_id == page_id
                        ).first()

                        profile: Dict[str, Any] = {}
                        need_profile = not chat or (chat and chat.username.startswith(("FB User", "User")))
                        if need_profile:
                            token, token_page_id, token_source = _resolve_facebook_profile_token(
                                db,
                                facebook_user_id=sender_id,
                                preferred_page=fb_page
                            )
                            if not token:
                                logger.warning(
                                    "No access token available for Facebook profile lookup (user=%s)",
                                    sender_id
                                )
                            else:
                                profile_result = await facebook_client.get_user_profile(
                                    page_access_token=token,
                                    user_id=sender_id
                                )
                                if profile_result.get("success"):
                                    profile = profile_result
                                else:
                                    logger.warning(
                                        "Facebook profile lookup failed for %s via %s token (page=%s): %s",
                                        sender_id,
                                        token_source,
                                        token_page_id or "n/a",
                                        profile_result.get("error")
                                    )

                        profile_name = profile.get("name") if isinstance(profile, dict) else None
                        if not profile_name and isinstance(profile, dict):
                            first_name = profile.get("first_name")
                            last_name = profile.get("last_name")
                            full_name = " ".join(part for part in [first_name, last_name] if part).strip()
                            profile_name = full_name or None
                        if not profile_name:
                            if not FACEBOOK_ACCESS_TOKEN_BACKUP:
                                logger.error("FACEBOOK_ACCESS_TOKEN_BACKUP is not set; cannot fetch Facebook user name via Graph API")
                            else:
                                graph_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{sender_id}?fields=name&access_token={FACEBOOK_ACCESS_TOKEN_BACKUP}"
                                try:
                                    graph_resp = requests.get(graph_url, timeout=5)
                                except requests.RequestException as exc:
                                    logger.error("Graph API user name lookup failed for %s: %s", sender_id, exc)
                                else:
                                    if graph_resp.status_code == 200:
                                        profile_name = (graph_resp.json() or {}).get("name") or profile_name
                                    else:
                                        logger.warning(
                                            "Graph API user name lookup failed for %s: status=%s body=%s",
                                            sender_id,
                                            graph_resp.status_code,
                                            graph_resp.text
                                        )
                        profile_pic_url = profile.get("profile_pic") if isinstance(profile, dict) else None
                        if not profile_pic_url and isinstance(profile, dict):
                            profile_pic_url = profile.get("profile_pic_url")
                        if not profile_pic_url:
                            profile_pic_url = f"https://via.placeholder.com/150?text={sender_id[:8]}"
                        computed_username = profile_name or processed.get("sender_name") or f"FB User {sender_id[:8]}"

                        facebook_user = db.query(FacebookUser).filter(FacebookUser.id == sender_id).first()
                        if not facebook_user:
                            facebook_user = FacebookUser(
                                id=sender_id,
                                username=computed_username,
                                name=profile_name,
                                profile_pic_url=profile_pic_url,
                                last_message=processed.get("text", ""),
                            )
                            db.add(facebook_user)
                            db.flush()
                        else:
                            facebook_user.last_message = processed.get("text", "") or facebook_user.last_message
                            facebook_user.last_seen_at = utc_now()
                            if profile_name:
                                facebook_user.name = profile_name
                            if computed_username:
                                facebook_user.username = computed_username
                            if profile_pic_url:
                                facebook_user.profile_pic_url = profile_pic_url

                        if not chat:
                            temp_instagram_id = facebook_user.id if _requires_sqlite_instagram_fallback(db) else None
                            chat = Chat(
                                facebook_user_id=facebook_user.id,
                                instagram_user_id=temp_instagram_id,
                                username=computed_username,
                                profile_pic_url=profile_pic_url,
                                platform=MessagePlatform.FACEBOOK,
                                facebook_page_id=page_id,
                                status=ChatStatus.UNASSIGNED
                            )
                            db.add(chat)
                            db.flush()
                            if not lead_form:
                                assigned_agent = _assign_chat_round_robin(db, chat)
                                if assigned_agent:
                                    chat.assigned_agent = assigned_agent
                        elif not chat.facebook_user_id:
                            chat.facebook_user_id = facebook_user.id

                        if need_profile:
                            chat.username = computed_username
                            chat.profile_pic_url = profile_pic_url


                        event_timestamp = utc_now()
                        new_message = create_chat_message_record(
                            chat,
                            sender=MessageSender.FACEBOOK_USER,
                            content=processed.get("text", ""),
                            message_type=MessageType.TEXT,
                            timestamp=event_timestamp,
                            is_ticklegram=False,
                            is_lead_form_message=lead_form,
                            metadata_json=fb_metadata_json
                        )
                        new_message.attachments = []
                        db.add(new_message)

                        if lead_form:
                            _clear_assignment_for_lead_form(chat)

                        # Update chat
                        chat.last_message = processed.get("text", "")
                        chat.unread_count += 1
                        chat.last_incoming_at = event_timestamp
                        chat.updated_at = event_timestamp
                        
                        db.commit()
                        db.refresh(new_message)
                        processed_messaging_event = True
                        logger.info(f"Processed Facebook message from {sender_id} on page {page_id}")
                        
                        # Notify relevant users about new message
                        notify_users = set()
                        
                        # Add assigned agent if any
                        if chat.assigned_to:
                            notify_users.add(str(chat.assigned_to))
                        
                        # Add admin users
                        admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
                        notify_users.update(str(user.id) for user in admin_users)
                        
                        message_payload = MessageResponse.model_validate(new_message).model_dump(mode="json")

                        # Broadcast new message notification
                        await ws_manager.broadcast_to_users(notify_users, {
                            "type": "new_message",
                            "chat_id": str(chat.id),
                            "platform": chat.platform.value,
                            "sender_id": sender_id,
                            "message": message_payload
                        })
        
        if not processed_messaging_event:
            db.commit()

        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Error processing Facebook webhook: {e}")
        # Return 200 to avoid Facebook retrying
        return {"status": "error", "message": str(e)}

# --- Chat assignment helpers ---
class AssignChatByEmployeeRequest(BaseModel):
    chat_id: str
    employee_id: str


@api_router.post("/admin/assign-chat")
def assign_chat_by_employee(
    payload: AssignChatByEmployeeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assign a chat to an agent resolved by employee_id.
    Agents and admins can use this to route inquiries back to their owner.
    """
    chat = db.query(Chat).filter(Chat.id == payload.chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    agent = (
        db.query(User)
        .options(joinedload(User.position))
        .filter(func.lower(User.emp_id) == payload.employee_id.strip().lower())
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found for employee_id")
    if not _is_assignable_agent(agent):
        raise HTTPException(status_code=400, detail="Agent is inactive")

    chat.assigned_to = agent.id
    chat.status = ChatStatus.ASSIGNED
    db.commit()
    db.refresh(chat)
    logger.info("Chat %s assigned by emp_id %s (user=%s)", payload.chat_id, payload.employee_id, current_user.id)
    return {"success": True, "chat": ChatResponse.model_validate(chat)}

# ============= MOCK DATA GENERATOR =============
from generate_mock_data import generate_mock_chats as generate_mock_data

@api_router.post("/mock/generate-chats")
def generate_mock_chats(
    count: int = 5,
    platform: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Generate mock chats for testing (Instagram or Facebook)"""
    chat_ids = generate_mock_data(
        db=db,
        user_id=current_user.id,
        count=count,
        platform=platform or "INSTAGRAM"
    )
    
    logger.info(f"Generated {count} mock chats")
    return {
        "success": True,
        "count": count,
        "platform": platform or "INSTAGRAM",
        "chat_ids": chat_ids
    }

@api_router.post("/mock/simulate-message")
def simulate_incoming_message(chat_id: str, message: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Simulate an incoming Instagram message"""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    new_message = create_chat_message_record(
        chat,
        sender=MessageSender.INSTAGRAM_USER if chat.platform == MessagePlatform.INSTAGRAM else MessageSender.FACEBOOK_USER,
        content=message,
        message_type=MessageType.TEXT,
        timestamp=utc_now(),
        is_ticklegram=False
    )
    new_message.attachments = []
    db.add(new_message)
    
    chat.last_message = message
    chat.unread_count += 1
    now_time = utc_now()
    chat.last_incoming_at = now_time if chat.platform == MessagePlatform.INSTAGRAM else chat.last_incoming_at
    chat.updated_at = now_time
    
    db.commit()
    db.refresh(new_message)
    
    logger.info(f"Simulated incoming message for chat {chat_id}")
    return {"success": True, "message": MessageResponse.model_validate(new_message)}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    user_id: Optional[str] = None
    try:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            logger.error("WebSocket connection rejected: No token provided")
            return

        payload = decode_access_token(token)
        if not payload or "user_id" not in payload:
            await websocket.close(code=4002, reason="Invalid authentication token")
            logger.error("WebSocket connection rejected: Invalid token")
            return

        user_id = str(payload["user_id"])
        user = db.query(User).filter(User.id == payload["user_id"]).first()
        if not user:
            await websocket.close(code=4003, reason="User not found")
            logger.error("WebSocket connection rejected: User not found")
            user_id = None
            return

        await ws_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connected for user {user_id}")

        while True:
            try:
                data = await websocket.receive_json()
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                logger.debug(f"Received WebSocket message from user {user_id}: {data}")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user_id}")
                break
            except ValueError as json_error:
                logger.warning(f"Invalid JSON received from user {user_id}: {json_error}")
            except Exception as err:
                logger.error(f"Error handling WebSocket message from user {user_id}: {err}")
    except Exception as error:
        logger.error(f"WebSocket authentication/processing error: {error}")
        if websocket.application_state == WebSocketState.CONNECTING:
            await websocket.close(code=4004, reason="Authentication failed")
    finally:
        if user_id:
            try:
                ws_manager.disconnect(websocket, user_id)
                logger.info(f"WebSocket connection cleaned up for user {user_id}")
            except Exception as cleanup_error:
                logger.error(f"Error during WebSocket cleanup: {cleanup_error}")


# Include the router in the main app
app.include_router(auth_routes.router, prefix="/api")
app.include_router(user_routes.router, prefix="/api")
app.include_router(api_router)

# Configure CORS
# cors_origins = ["*"]  # Allow all origins

# app.add_middleware(
#     CORSMiddleware,
#     allow_credentials=True,
#     allow_origins=cors_origins,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["*"]
# )

# Configure CORS
cors_origins_str = os.getenv('CORS_ORIGINS', '*').strip()
if cors_origins_str == '*':
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    origins = [origin.strip() for origin in cors_origins_str.split(',') if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
