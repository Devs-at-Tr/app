## Auth UX refresh

- Login card keeps the existing centered layout/branding but adopts a softer gradient panel, glowing focus states, and a dedicated `Forgot password?` link that routes to `/forgot-password`.
- The former self-service sign-up link is hidden. When public signup is disabled the card shows a short “Access is restricted” reminder instead.
- Both `/forgot-password` and `/reset-password` pages reuse the same gradient shell with concise copy and neutral confirmations to avoid user enumeration.

## Public signup toggle

- `ALLOW_PUBLIC_SIGNUP` (default `false`) gates `/api/auth/signup`. When disabled, the endpoint returns `403` and the frontend route immediately redirects to `/login` with a friendly banner.
- `GET /api/auth/config` surfaces `{ allow_public_signup, forgot_password_enabled }` so the React app can keep UI, routing, and backend behaviour in sync.
- Frontend still keeps the `SignupPage` component for future use; it is only mounted when the flag is explicitly enabled.

## Forgot + reset password flow

- New routes:
  - `POST /api/auth/forgot-password` accepts an email, silently creates a one-time token, and emails a branded link using `utils/mailer.send_email`.
  - `POST /api/auth/reset-password` validates the token, rotates the user’s bcrypt hash, and retires every outstanding token for that user.
- Tokens live in the new `password_reset_tokens` table (see migration `20251114_150000_password_reset_tokens.py`) with `expires_at`, `used_at`, and a SHA-256 hash of the secret.
- Frontend UX:
  - `/forgot-password` collects the email, mentions “if your account exists”, and always renders the same confirmation.
  - `/reset-password?token=…` accepts the token, validates password+confirm locally, and returns users to `/login` with a success banner once complete.
- Env knobs: `ENABLE_FORGOT_PASSWORD`, `PASSWORD_RESET_TOKEN_MINUTES`, `FRONTEND_BASE_URL`, `SUPPORT_CONTACT_EMAIL`, the SMTP settings listed below, and `PASSWORD_RESET_EMAIL_SUBJECT`.

### Password reset SMTP configuration

Password reset emails now use a simple SMTP relay—no paid provider required. Point the following env vars at any standard SMTP server (self-hosted Mailcow, Gmail/Outlook SMTP, etc.):

- `SMTP_HOST` / `SMTP_PORT` – address and port of your SMTP server (e.g., `smtp.gmail.com:587`).
- `SMTP_USER` / `SMTP_PASS` – credentials for the SMTP account (leave blank for anonymous relays).
- `SMTP_USE_TLS` – set to `true` to enable STARTTLS (recommended).
- `SMTP_FROM_EMAIL` / `SMTP_FROM_NAME` – default “from” address and label shown to recipients.

If the SMTP config is missing, the API still responds with a generic success message but logs that email delivery was skipped, so production deployments should always configure these values.

## Admin “Create User”

- Navigation: Any user with `user:invite` permission now sees a “Create User” link (icon: `UserPlus`) in the sidebar under management utilities.
- UI: `/admin/users/new` uses the standard dashboard shell with an admin form card. Fields: name, email, password (prefilled `1234`, editable), role selector (Agent/Admin), and optional position dropdown (auto-populated when the operator can read positions).
- Backend: `POST /api/admin/users` (protected by `user:invite`) accepts `{ name, email, password, role, position_id }`, hashes the password, attaches the requested position or defaults intelligently, and returns a full `UserResponse`.

## File inventory

**Created**
- `backend/migrations/20251114_150000_password_reset_tokens.py`
- `backend/utils/mailer.py`
- `frontend/src/pages/ForgotPasswordPage.js`
- `frontend/src/pages/ResetPasswordPage.js`
- `frontend/src/pages/CreateUserPage.jsx`
- `docs/Auth-UX-and-User-Management.md`

**Significantly modified**
- `backend/server.py`, `backend/models.py`, `backend/schemas.py`, `backend/.env_example`
- `frontend/src/App.js`, `frontend/src/pages/LoginPage.js`, `frontend/src/pages/InboxPage.js`
- `frontend/src/pages/CommentsPage.js`, `frontend/src/pages/TemplatesPage.js`, `frontend/src/pages/PositionsPage.jsx`, `frontend/src/pages/UserDirectoryPage.jsx`
- `frontend/src/utils/navigationConfig.js`

**Changelog highlights**
- Added password reset infrastructure (DB model, migration, env config, mailer, API endpoints, and React flows).
- Hardened authentication UX: modernized login, introduced forgot/reset routes, and disabled public signup behind a shared config flag.
- Delivered admin-controlled account provisioning with a permission-aware sidebar entry, dashboard form, and secure backend endpoint.
