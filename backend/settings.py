import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

ALLOW_PUBLIC_SIGNUP = os.getenv("ALLOW_PUBLIC_SIGNUP", "false").lower() in {"1", "true", "yes"}
PASSWORD_RESET_TOKEN_LIFETIME_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "60"))
FRONTEND_BASE_URL = (
    os.getenv("FRONTEND_BASE_URL")
    or os.getenv("APP_BASE_URL")
    or os.getenv("PUBLIC_APP_URL")
    or os.getenv("FRONTEND_URL")
)
FORGOT_PASSWORD_ENABLED = os.getenv("ENABLE_FORGOT_PASSWORD", "true").lower() in {"1", "true", "yes"}
PASSWORD_RESET_EMAIL_SUBJECT = os.getenv(
    "PASSWORD_RESET_EMAIL_SUBJECT", "Reset your TickleGram password"
)
PASSWORD_RESET_EMAIL_CONTACT = os.getenv("SUPPORT_CONTACT_EMAIL", "support@ticklegram.com")
