"""
Fetch and update Facebook user names using the Graph API.

Usage:
    python update_facebook_names.py

Requirements:
    - FACEBOOK_ACCESS_TOKEN_BACKUP must be set in the environment (.env is loaded)
    - Requests dependency is already present in requirements.txt
"""
import logging
import os
from pathlib import Path
from typing import Iterator, Optional, Tuple

import requests
from dotenv import load_dotenv

from database import SessionLocal
from models import FacebookUser, FacebookPage, Chat, MessagePlatform

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v18.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN_BACKUP")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("fb-name-updater")


def fetch_profile(user_id: str, token: str, source: str) -> Tuple[Optional[str], Optional[str]]:
    if not token:
        logger.warning("No token provided for %s; skipping", user_id)
        return None, None
    url = f"{GRAPH_BASE}/{user_id}"
    params = {
        "fields": "name,first_name,last_name,profile_pic",
        "access_token": token,
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
    except requests.RequestException as exc:
        logger.warning("Request failed for %s via %s: %s", user_id, source, exc)
        return None, None
    if resp.status_code != 200:
        logger.warning(
            "Graph API error for %s via %s: status=%s body=%s",
            user_id,
            source,
            resp.status_code,
            resp.text,
        )
        return None, None
    data = resp.json() or {}
    name = data.get("name")
    if not name:
        first = (data.get("first_name") or "").strip()
        last = (data.get("last_name") or "").strip()
        combined = " ".join(part for part in [first, last] if part).strip()
        name = combined or None
    profile_pic = data.get("profile_pic") or data.get("profile_pic_url")
    return name, profile_pic


def iter_tokens_for_user(db_session: SessionLocal, user_id: str) -> Iterator[Tuple[str, str]]:
    """Yield candidate tokens for this user in priority order."""
    seen_pages = set()
    chat_q = (
        db_session.query(Chat.facebook_page_id)
        .filter(Chat.facebook_user_id == user_id, Chat.facebook_page_id.isnot(None))
        .order_by(Chat.updated_at.desc())
    )
    for (page_id,) in chat_q:
        if not page_id or page_id in seen_pages:
            continue
        seen_pages.add(page_id)
        page = (
            db_session.query(FacebookPage)
            .filter(FacebookPage.page_id == page_id, FacebookPage.is_active.is_(True))
            .first()
        )
        if page and page.access_token:
            yield page.access_token, f"page:{page.page_id}"
    if ACCESS_TOKEN:
        yield ACCESS_TOKEN, "backup"


def update_missing_names() -> None:
    with SessionLocal() as db:
        candidates = (
            db.query(FacebookUser)
            .filter(
                (FacebookUser.name.is_(None))
                | (FacebookUser.name == "")
                | (FacebookUser.username.ilike("fb user%"))
            )
            .all()
        )
        logger.info("Found %d Facebook users needing names", len(candidates))
        updated = 0
        for user in candidates:
            resolved_name: Optional[str] = None
            resolved_pic: Optional[str] = None
            for token, source in iter_tokens_for_user(db, user.id):
                name, pic = fetch_profile(user.id, token, source)
                if name or pic:
                    resolved_name = resolved_name or name
                    resolved_pic = resolved_pic or pic
                    break
            if not resolved_name and not resolved_pic:
                logger.debug("No name resolved for %s after all token attempts", user.id)
                continue
            if resolved_name:
                user.name = resolved_name
                if not user.username or user.username.lower().startswith("fb user"):
                    user.username = resolved_name
            if resolved_pic:
                user.profile_pic_url = resolved_pic
            updated += 1
            db.add(user)

            if resolved_name or resolved_pic:
                chats = (
                    db.query(Chat)
                    .filter(
                        Chat.facebook_user_id == user.id,
                        Chat.platform == MessagePlatform.FACEBOOK,
                    )
                    .all()
                )
                for chat in chats:
                    if resolved_name and (not chat.username or chat.username.startswith("FB User")):
                        chat.username = resolved_name
                    if resolved_pic and (not chat.profile_pic_url or "placeholder" in chat.profile_pic_url.lower()):
                        chat.profile_pic_url = resolved_pic
                    db.add(chat)

            if updated % 20 == 0:
                db.commit()
                logger.info("Committed %d updates so far", updated)
        db.commit()
        logger.info("Finished. Updated %d user names.", updated)


if __name__ == "__main__":
    update_missing_names()
