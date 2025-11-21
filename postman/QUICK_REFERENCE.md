# Backend API - Quick Reference Guide

## 🚀 Base URL
```
Local: http://localhost:8000
Production: https://api.example.com
```

## 🔑 Authentication
```bash
# Login
POST /api/auth/login
Body: { "email": "user@example.com", "password": "password" }
Response: { "access_token": "...", "token_type": "bearer" }

# Use token in headers
Authorization: Bearer <token>
```

---

## 📋 Quick Endpoint Reference

### Authentication
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register user (admin) | ✅ Admin |
| POST | `/api/auth/signup` | Public signup | ❌ |
| GET | `/api/auth/config` | Get auth config | ❌ |
| POST | `/api/auth/forgot-password` | Request reset | ❌ |
| POST | `/api/auth/reset-password` | Reset password | ❌ |
| POST | `/api/auth/login` | Login | ❌ |
| GET | `/api/auth/me` | Current user | ✅ |

### Users
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/users` | List all users | ✅ Admin |
| GET | `/api/users/agents` | List agents | ✅ |
| GET | `/api/users/roster` | User roster | ✅ |
| PATCH | `/api/users/{id}/active` | Update active state | ✅ |
| POST | `/api/admin/users` | Create user | ✅ Admin |
| POST | `/api/users/{id}/position` | Assign position | ✅ |

### Positions
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/positions` | List positions | ✅ |
| POST | `/api/positions` | Create position | ✅ |
| PUT | `/api/positions/{id}` | Update position | ✅ |
| DELETE | `/api/positions/{id}` | Delete position | ✅ |
| GET | `/api/permissions/codes` | List permissions | ✅ |

### Chats
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/chats` | List chats | ✅ |
| GET | `/api/chats/{id}` | Get chat details | ✅ |
| POST | `/api/chats/{id}/assign` | Assign chat | ✅ |
| POST | `/api/chats/{id}/mark_read` | Mark as read | ✅ |
| POST | `/api/chats/{id}/message` | Send message | ✅ |

**Chat Filters:**
- `?status_filter=open|closed|pending`
- `?assigned_to_me=true`
- `?platform=instagram|facebook`
- `?assigned_to={user_id}`
- `?unseen=true`
- `?not_replied=true`

### Templates
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/templates` | List templates | ✅ |
| POST | `/api/templates` | Create template | ✅ Admin |
| PUT | `/api/templates/{id}` | Update template | ✅ Admin |
| DELETE | `/api/templates/{id}` | Delete template | ✅ Admin |
| POST | `/api/templates/{id}/submit-to-meta` | Submit to Meta | ✅ Admin |
| GET | `/api/templates/{id}/meta-status` | Check Meta status | ✅ Admin |
| POST | `/api/templates/{id}/send` | Send template | ✅ |

### Instagram - Comments
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/instagram/comments` | List comments | ✅ |
| POST | `/api/instagram/comments/{id}/reply` | Reply to comment | ✅ |
| POST | `/api/comments/create` | Create comment | ✅ |
| POST | `/api/comments/hide` | Hide/unhide comment | ✅ |
| DELETE | `/api/comments/delete` | Delete comment | ✅ |

### Instagram - Insights
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/instagram/mentions` | Get mentions | ✅ |
| GET | `/api/insights/account` | Account insights | ✅ |
| GET | `/api/insights/media` | Media insights | ✅ |
| GET | `/api/insights/story` | Story insights | ✅ |

### Instagram - Accounts
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/instagram/accounts` | Connect account | ✅ Admin |
| GET | `/api/instagram/accounts` | List accounts | ✅ Admin |
| GET | `/api/instagram/accounts/{id}` | Get account | ✅ Admin |
| DELETE | `/api/instagram/accounts/{id}` | Delete account | ✅ Admin |

### Facebook
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/facebook/comments` | List comments | ✅ |
| POST | `/api/facebook/comments/{id}/reply` | Reply to comment | ✅ |
| POST | `/api/facebook/pages` | Connect page | ✅ Admin |
| GET | `/api/facebook/pages` | List pages | ✅ |
| GET | `/api/facebook/pages/{id}` | Get page | ✅ |
| PATCH | `/api/facebook/pages/{id}` | Update page | ✅ |
| DELETE | `/api/facebook/pages/{id}` | Delete page | ✅ Admin |

### Dashboard
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/dashboard/stats` | Get statistics | ✅ |

### Webhooks
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/webhooks/instagram` | IG webhook verify | ❌ |
| POST | `/api/webhooks/instagram` | IG webhook handler | ❌ |
| GET | `/api/webhooks/facebook` | FB webhook verify | ❌ |
| POST | `/api/webhooks/facebook` | FB webhook handler | ❌ |
| GET | `/webhook` | Meta verify | ❌ |
| POST | `/webhook` | Meta handler | ❌ |

### Mock & Testing
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/mock/generate-chats` | Generate mock chats | ✅ |
| POST | `/api/mock/simulate-message` | Simulate message | ✅ |

### Developer
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/dev/db-overview` | DB overview | ✅ Super Admin |

---

## 📦 Common Request Bodies

### Login
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

### Register User
```json
{
  "email": "newuser@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe",
  "role": "agent"
}
```

### Create Position
```json
{
  "name": "Senior Agent",
  "description": "Senior customer support agent",
  "permissions": ["chat.view", "chat.assign", "chat.message"]
}
```

### Assign Chat
```json
{
  "assigned_to": "user_id_here"
}
```

### Send Message
```json
{
  "text": "Hello! How can I help you today?",
  "message_type": "text"
}
```

### Create Template
```json
{
  "name": "Welcome Message",
  "content": "Welcome to our service!",
  "platform": "instagram",
  "category": "greeting",
  "language": "en"
}
```

### Connect Instagram Account
```json
{
  "instagram_business_account_id": "ig_account_id",
  "access_token": "access_token_here",
  "page_id": "facebook_page_id"
}
```

### Connect Facebook Page
```json
{
  "page_id": "facebook_page_id",
  "access_token": "page_access_token",
  "page_name": "My Business Page"
}
```

---

## 🎯 Common Workflows

### 1. Agent Login & View Chats
```bash
# 1. Login
POST /api/auth/login
Body: { "email": "agent@example.com", "password": "password" }

# 2. Get my profile
GET /api/auth/me

# 3. View my assigned chats
GET /api/chats?assigned_to_me=true&status_filter=open

# 4. View unseen chats
GET /api/chats?unseen=true
```

### 2. Handle a Customer Chat
```bash
# 1. Get chat details
GET /api/chats/{chat_id}

# 2. Assign to myself (if not assigned)
POST /api/chats/{chat_id}/assign
Body: { "assigned_to": "my_user_id" }

# 3. Send a message
POST /api/chats/{chat_id}/message
Body: { "text": "Hello! How can I help?", "message_type": "text" }

# 4. Mark as read
POST /api/chats/{chat_id}/mark_read
```

### 3. Use a Template
```bash
# 1. List available templates
GET /api/templates?platform=instagram

# 2. Send template
POST /api/templates/{template_id}/send
Body: { "chat_id": "chat_id_here", "variables": { "name": "John" } }
```

### 4. Admin: Create New Agent
```bash
# 1. Create user
POST /api/admin/users
Body: {
  "email": "newagent@example.com",
  "password": "SecurePass123!",
  "full_name": "New Agent",
  "role": "agent",
  "is_active": true
}

# 2. Assign position
POST /api/users/{user_id}/position
Body: { "position_id": "position_id_here" }
```

### 5. Admin: Setup Instagram
```bash
# 1. Connect Instagram account
POST /api/instagram/accounts
Body: {
  "instagram_business_account_id": "ig_id",
  "access_token": "token",
  "page_id": "page_id"
}

# 2. View comments
GET /api/instagram/comments

# 3. Reply to comment
POST /api/instagram/comments/{comment_id}/reply
Body: { "text": "Thank you for your comment!" }
```

---

## 🔍 Response Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 500 | Server Error | Internal server error |

---

## 💡 Tips

1. **Auto-save token**: The Postman collection automatically saves your auth token after login
2. **Use filters**: Chat endpoints support multiple filters for efficient querying
3. **Webhooks**: Don't require authentication (verified by Meta)
4. **WebSocket**: Available at `/ws` for real-time updates
5. **Pagination**: Check response headers for pagination info on list endpoints

---

## 🐛 Troubleshooting

### 401 Unauthorized
- Check if token is expired
- Re-login to get a new token
- Verify token is in Authorization header

### 403 Forbidden
- Check user role and permissions
- Verify endpoint requires admin access
- Contact admin for permission changes

### 404 Not Found
- Verify endpoint URL is correct
- Check if resource ID exists
- Ensure resource is in your workspace

### 500 Server Error
- Check server logs
- Verify request body format
- Contact support if persists

---

**Last Updated**: $(date)
**API Version**: 1.0.0