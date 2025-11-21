# Backend API Documentation

This directory contains comprehensive API documentation for your backend server in multiple formats.

## 📁 Files Generated

### 1. **Postman Collection** (`Backend API.postman_collection.json`)
A complete Postman collection with all 60+ API endpoints organized by functional areas.

### 2. **OpenAPI Specification** (`backend-api-openapi.yaml`)
An OpenAPI 3.0 specification document that formally describes your API.

---

## 🚀 Quick Start

### Using the Postman Collection

#### Option 1: Import into Postman Desktop
1. Open Postman Desktop
2. Click **Import** button (top left)
3. Select the file: `postman/collections/Backend API.postman_collection.json`
4. The collection will appear in your workspace with all endpoints organized

#### Option 2: Use from Command Line
```bash
# Run the entire collection
newman run "postman/collections/Backend API.postman_collection.json" \
  --env-var "base_url=http://localhost:8000"

# Run a specific folder
newman run "postman/collections/Backend API.postman_collection.json" \
  --folder "Authentication" \
  --env-var "base_url=http://localhost:8000"
```

### Using the OpenAPI Specification

#### Import into Postman
1. Open Postman
2. Click **Import** → **Link**
3. Paste the path to `backend-api-openapi.yaml`
4. Postman will generate a collection from the spec

#### Generate Documentation
```bash
# Using Redoc
npx redoc-cli serve postman/specifications/backend-api-openapi.yaml

# Using Swagger UI
npx swagger-ui-watcher postman/specifications/backend-api-openapi.yaml
```

---

## 🔧 Configuration

### Environment Variables

The collection uses these variables (set them in Postman or your environment):

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | API base URL | `http://localhost:8000` |
| `auth_token` | JWT authentication token | Auto-set after login |

### Setting Up Environment

1. In Postman, create a new environment
2. Add variable `base_url` with your server URL
3. The `auth_token` will be automatically set when you login

---

## 📚 API Structure

### Authentication
- User registration (admin & public)
- Login with JWT tokens
- Password reset flow
- User profile management

### User Management
- List and manage users
- Agent roster with chat counts
- User activation/deactivation
- Position assignment

### Position Management
- Create and manage positions
- Permission management
- Role-based access control

### Instagram Integration
- **Comments**: List, reply, create, hide, delete
- **Mentions**: Track brand mentions
- **Insights**: Account, media, and story analytics
- **Marketing**: Conversion API events
- **Accounts**: Connect and manage IG Business accounts

### Facebook Integration
- **Comments**: List and reply to comments
- **Pages**: Connect and manage Facebook pages

### Chat Management
- List chats with advanced filtering
- Assign chats to agents
- Send messages
- Mark as read
- Real-time updates via WebSocket

### Templates
- Create and manage message templates
- Submit templates for Meta approval
- Send template messages with variables

### Dashboard
- Real-time statistics
- Chat metrics
- Agent performance

### Webhooks
- Instagram webhook handlers
- Facebook webhook handlers
- Unified Meta webhook endpoint

---

## 🔐 Authentication

Most endpoints require Bearer token authentication:

1. **Login** to get a token:
   ```bash
   POST /api/auth/login
   {
     "email": "user@example.com",
     "password": "password"
   }
   ```

2. **Use the token** in subsequent requests:
   ```
   Authorization: Bearer <your_token_here>
   ```

3. In Postman, the token is **automatically saved** after login!

---

## 📖 Endpoint Categories

### 🔑 Authentication (7 endpoints)
- Register, Login, Signup
- Password reset flow
- Get current user
- Auth configuration

### 👥 User Management (6 endpoints)
- List users and agents
- User roster
- Create and update users
- Manage active state

### 🎯 Position Management (5 endpoints)
- CRUD operations for positions
- Permission management
- Permission code listing

### 📸 Instagram (14 endpoints)
- Comments management
- Mentions tracking
- Insights (account, media, story)
- Marketing events
- Account management

### 📘 Facebook (7 endpoints)
- Comment management
- Page connection and management

### 💬 Chats (5 endpoints)
- List with filters
- Get details
- Assign to agents
- Send messages
- Mark as read

### 📝 Templates (7 endpoints)
- CRUD operations
- Meta approval workflow
- Send template messages

### 📊 Dashboard (1 endpoint)
- Comprehensive statistics

### 🔗 Webhooks (6 endpoints)
- Instagram webhook verification & handler
- Facebook webhook verification & handler
- Unified Meta webhook

### 🧪 Mock & Testing (2 endpoints)
- Generate mock chats
- Simulate messages

### 🛠️ Developer (1 endpoint)
- Database overview

---

## 🎯 Common Workflows

### 1. First Time Setup
```
1. POST /api/auth/login → Get token
2. GET /api/auth/me → Verify authentication
3. GET /api/users/agents → See available agents
4. GET /api/chats → View chats
```

### 2. Handle a Chat
```
1. GET /api/chats?unseen=true → Get unseen chats
2. POST /api/chats/{id}/assign → Assign to yourself
3. GET /api/chats/{id} → Get chat details
4. POST /api/chats/{id}/message → Send response
5. POST /api/chats/{id}/mark_read → Mark as read
```

### 3. Use Templates
```
1. GET /api/templates → List available templates
2. POST /api/templates/{id}/send → Send template to chat
```

### 4. Connect Instagram
```
1. POST /api/instagram/accounts → Connect account
2. GET /api/instagram/comments → View comments
3. POST /api/instagram/comments/{id}/reply → Reply
```

---

## 🧪 Testing

### Run All Tests
```bash
newman run "postman/collections/Backend API.postman_collection.json" \
  --environment your-environment.json \
  --reporters cli,json
```

### Test Specific Folder
```bash
newman run "postman/collections/Backend API.postman_collection.json" \
  --folder "Authentication" \
  --environment your-environment.json
```

---

## 📝 Notes

### Security
- Most endpoints require authentication
- Admin-only endpoints are clearly marked
- Webhooks don't require authentication (verified by Meta)

### Rate Limiting
- Check your server configuration for rate limits
- Instagram/Facebook APIs have their own rate limits

### WebSocket
- Real-time updates available at `/ws`
- Requires authentication token as query parameter

### Pagination
- Some list endpoints may support pagination
- Check response headers for pagination info

---

## 🤝 Contributing

When adding new endpoints:
1. Update the Postman collection
2. Update the OpenAPI specification
3. Update this README
4. Test thoroughly

---

## 📞 Support

For issues or questions:
- Check the API response error messages
- Review the endpoint descriptions
- Contact: support@example.com

---

## 📄 License

[Your License Here]

---

**Generated**: $(date)
**Total Endpoints**: 60+
**API Version**: 1.0.0