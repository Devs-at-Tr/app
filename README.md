# TickleGram Dashboard - Multi-Platform Messenger Management

A full-stack messaging management platform designed for teams to efficiently handle customer support and engagement through **Instagram DMs** and **Facebook Messenger**.

## 📚 Documentation Map

- **Project Guide** – consolidated quick-start, integration, and engineering notes now live in [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md). Refer to it for setup checklists, Meta permission collateral, bug-fix history, and AI prompt briefs.
- **README (this file)** – high-level product overview, feature list, and API surface.

## 🚀 Features

### Core Functionality
- **Multi-Platform Support** - Manage both Instagram DMs and Facebook Messenger in one interface
- **JWT Authentication** - Secure role-based access (Admin & Agent roles)
- **Real-time Chat Management** - View and manage messages from both platforms
- **Agent Assignment** - Assign chats to specific agents
- **Message History** - Full conversation history with timestamps
- **Dashboard Analytics** - Track total, assigned, and unassigned chats with platform breakdown
- **Platform Filtering** - Switch between Instagram, Facebook, or view all chats
- **Search & Filter** - Quickly find conversations
- **Facebook Page Management** - Connect and manage multiple Facebook pages
- **Hybrid API Mode** - Mock mode for development, real mode for production

### User Roles

#### Admin
- View all chats (assigned and unassigned)
- Assign/unassign chats to agents
- Access full dashboard statistics
- Manage agent accounts

#### Agent
- View only assigned chats
- Send and receive messages
- Track personal chat statistics

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL/SQLite** - Relational database with flexible support
- **SQLAlchemy** - ORM for database operations
- **JWT (PyJWT)** - Authentication tokens
- **Bcrypt** - Password hashing
- **httpx** - Async HTTP client for Facebook Graph API
- **Facebook Graph API** - Facebook Messenger integration

### Frontend
- **React** - UI framework
- **TailwindCSS** - Styling
- **shadcn/ui** - Component library
- **Axios** - HTTP client
- **React Router** - Navigation
- **Lucide Icons** - Icon library

## � Setup & Installation

### Prerequisites
- Python 3.8+
- Node.js 14+
- PostgreSQL (optional, SQLite works as fallback)

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Edit `backend/.env`:
   ```env
   # Database
   POSTGRES_URL=postgresql://ticklegram_user:ticklegram_pass@localhost:5433/ticklegram
   
   # JWT Configuration
   JWT_SECRET=your-secret-key-change-in-production
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_MINUTES=1440
   
   # Facebook Messenger Configuration
   FACEBOOK_MODE=mock  # Use 'real' for production with actual Facebook API
   FACEBOOK_APP_ID=your_facebook_app_id
   FACEBOOK_APP_SECRET=your_facebook_app_secret
   FACEBOOK_WEBHOOK_VERIFY_TOKEN=ticklegram_fb_verify
   FACEBOOK_API_VERSION=v20.0
   ```

4. **Run database migration (if needed)**
   ```bash
   python migration_add_facebook_support.py
   ```

5. **Seed demo data (optional)**
   ```bash
   python seed_data.py
   ```

6. **Start the backend server**
   ```bash
   uvicorn server:app --reload --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   
   Edit `frontend/.env`:
   ```env
   REACT_APP_BACKEND_URL=http://localhost:8000
   REACT_APP_FACEBOOK_APP_ID=your_facebook_app_id
   ```

4. **Start the development server**
   ```bash
   npm start
   ```

5. **Access the application**
   
   Open http://localhost:3000 in your browser

## 📸 Instagram DM Setup

For complete Instagram integration instructions, see **[INSTAGRAM_INTEGRATION_GUIDE.md](./INSTAGRAM_INTEGRATION_GUIDE.md)**

### Quick Setup
1. Convert Instagram account to Business Account
2. Connect to a Facebook Page
3. Get Instagram Account ID and Page Access Token
4. Add credentials in Dashboard → "Manage Instagram"

### For Development (Mock Mode)
1. Set `INSTAGRAM_MODE=mock` in backend `.env`
2. No Instagram credentials required
3. Use mock data generators to test functionality

### For Production (Real API)
1. Set `INSTAGRAM_MODE=real` in backend `.env`
2. Configure webhook at `https://your-domain.com/api/webhooks/instagram`
3. See [INSTAGRAM_INTEGRATION_GUIDE.md](./INSTAGRAM_INTEGRATION_GUIDE.md) for detailed steps

---

## 🔧 Facebook Messenger Setup

### For Development (Mock Mode)
1. Set `FACEBOOK_MODE=mock` in backend `.env`
2. No Facebook App required
3. Use mock data generators to test functionality

### For Production (Real API)

1. **Create Facebook App**
   - Go to https://developers.facebook.com
   - Create a new app
   - Add "Messenger" product

2. **Configure Webhook**
   - Callback URL: `https://your-domain.com/api/webhooks/facebook`
   - Verify Token: Use value from `FACEBOOK_WEBHOOK_VERIFY_TOKEN`
   - Subscribe to: `messages`, `messaging_postbacks`

3. **Get Page Access Token**
   - In Facebook App Dashboard, go to Messenger > Settings
   - Generate Page Access Token for your Facebook page
   - Copy the token

4. **Connect Facebook Page in App**
   - Login as Admin
   - Click "Manage Facebook Pages"
   - Enter Page ID and Access Token
   - Save

5. **Update Environment Variables**
   ```env
   FACEBOOK_MODE=real
   FACEBOOK_APP_ID=your_actual_app_id
   FACEBOOK_APP_SECRET=your_actual_app_secret
   ```

6. **Test Webhook**
   - Send a message to your Facebook page
   - Check if it appears in the dashboard

## �🔑 Demo Credentials

### Admin Account
- Email: `admin@ticklegram.com`
- Password: `admin123`

### Agent Accounts
- Email: `agent1@ticklegram.com` / Password: `agent123`
- Email: `agent2@ticklegram.com` / Password: `agent123`

## 📚 API Documentation

Base URL: Check `/app/frontend/.env` for `REACT_APP_BACKEND_URL`

### Authentication Endpoints
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user

### Chat Management Endpoints
- `GET /api/chats` - List all chats (supports `?platform=instagram|facebook` filter)
- `GET /api/chats/{id}` - Get chat with messages
- `POST /api/chats/{id}/message` - Send message (auto-detects platform)
- `POST /api/chats/{id}/assign` - Assign chat to agent

### Facebook Messenger Endpoints
- `POST /api/facebook/pages` - Connect a Facebook page
- `GET /api/facebook/pages` - List all connected Facebook pages
- `GET /api/facebook/pages/{page_id}` - Get specific Facebook page
- `PATCH /api/facebook/pages/{page_id}` - Update Facebook page (toggle active status)
- `DELETE /api/facebook/pages/{page_id}` - Delete Facebook page
- `GET /api/webhooks/facebook` - Facebook webhook verification
- `POST /api/webhooks/facebook` - Receive Facebook messages

### Dashboard & Analytics
- `GET /api/dashboard/stats` - Get dashboard statistics (includes platform breakdown)
- `GET /api/users/agents` - List all agents (admin only)

### Development/Testing Endpoints
- `POST /api/mock/generate-chats` - Generate mock chats (supports `?platform=instagram|facebook`)
- `POST /api/mock/simulate-message` - Simulate incoming message

## 💡 Usage Guide

### For Admins

1. **Dashboard Overview**
   - View total chats with Instagram/Facebook breakdown
   - Monitor assigned vs unassigned chats
   - Track active agent count

2. **Managing Facebook Pages**
   - Click "Manage Facebook Pages" button
   - Add new Facebook page with Page ID and Access Token
   - Toggle pages active/inactive
   - Delete pages when no longer needed

3. **Platform Filtering**
   - Use platform selector to filter chats:
     - **All Platforms** - View all chats
     - **Instagram** - Only Instagram DMs
     - **Facebook** - Only Facebook Messenger chats

4. **Agent Assignment**
   - Open any chat
   - Select agent from dropdown
   - Chat automatically assigned to selected agent

5. **Generating Test Data**
   - Use mock endpoints to generate test chats
   - Specify platform parameter for Instagram or Facebook chats

### For Agents

1. **View Assigned Chats**
   - Only see chats assigned to you
   - Platform icons indicate source (Instagram/Facebook)
   - Unread count shown on each chat

2. **Responding to Messages**
   - Select a chat from sidebar
   - Type message in input field
   - Click send or press Enter
   - Messages automatically sent to correct platform

3. **Search & Filter**
   - Use search bar to find specific conversations
   - Platform filter applies to your assigned chats

### Platform Indicators

- 🎯 **Pink Icon** = Instagram DM
- 🔵 **Blue Icon** = Facebook Messenger
- Chat headers show platform badge
- Platform colors used throughout UI for easy identification

## 🎯 Key Features

### UI/UX
- Modern dark theme with purple/pink gradients
- Responsive design
- Platform-specific icons and colors (Instagram = Pink, Facebook = Blue)
- Platform filter selector (All, Instagram, Facebook)
- Intuitive chat interface with platform indicators

### Authentication & Security
- Role-based access control (Admin & Agent)
- JWT token authentication
- Webhook signature verification for Facebook
- Secure password hashing

### Multi-Platform Management
- Unified inbox for Instagram and Facebook
- Platform-aware message sending
- Facebook page connection and management (Admin only)
- Toggle active/inactive status for Facebook pages
- Platform breakdown in analytics dashboard

### Development Features
- Hybrid mode support (Mock/Real API)
- Mock data generators for testing
- Database migration scripts
- Comprehensive error handling
# vite
