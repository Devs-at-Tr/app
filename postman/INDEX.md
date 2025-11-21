# Backend API Documentation - Complete Package

## 📦 What's Included

This package contains comprehensive API documentation for your backend server in multiple formats, ready to use with Postman or any OpenAPI-compatible tool.

### Files Structure
```
postman/
├── README.md                          # Main documentation guide
├── QUICK_REFERENCE.md                 # Quick endpoint reference
├── INDEX.md                           # This file
├── collections/
│   └── Backend API.postman_collection.json    # Complete Postman collection (60+ endpoints)
├── environments/
│   ├── Backend API - Local.postman_environment.json      # Local dev environment
│   └── Backend API - Production.postman_environment.json # Production environment
└── specifications/
    └── backend-api-openapi.yaml       # OpenAPI 3.0 specification
```

---

## 🎯 Quick Start Guide

### For Postman Users (Recommended)

1. **Import the Collection**
   - Open Postman
   - Click **Import** button
   - Select `collections/Backend API.postman_collection.json`
   - ✅ All 60+ endpoints are now available!

2. **Import an Environment**
   - Click **Import** again
   - Select `environments/Backend API - Local.postman_environment.json`
   - Select the environment from the dropdown (top right)

3. **Start Testing**
   - Go to **Authentication** folder
   - Run the **Login** request
   - Your auth token is automatically saved!
   - All other requests will now work

### For OpenAPI/Swagger Users

1. **View in Swagger UI**
   ```bash
   npx swagger-ui-watcher postman/specifications/backend-api-openapi.yaml
   ```

2. **Generate Documentation**
   ```bash
   npx redoc-cli serve postman/specifications/backend-api-openapi.yaml
   ```

3. **Import into Postman**
   - Postman → Import → Select the YAML file
   - Postman will generate a collection automatically

---

## 📚 Documentation Files

### 1. README.md
**Purpose**: Complete documentation guide  
**Contains**:
- Detailed setup instructions
- Environment configuration
- API structure overview
- Common workflows
- Testing guidelines
- Troubleshooting tips

**When to use**: First time setup, understanding the API structure

### 2. QUICK_REFERENCE.md
**Purpose**: Quick lookup for developers  
**Contains**:
- All endpoints in table format
- Common request bodies
- Response codes
- Quick workflows
- Troubleshooting tips

**When to use**: Daily development, quick endpoint lookup

### 3. Backend API.postman_collection.json
**Purpose**: Executable API collection  
**Contains**:
- 60+ pre-configured requests
- Organized into 11 functional folders
- Auto-authentication setup
- Example request bodies
- Collection-level auth

**When to use**: Testing APIs, integration testing, automation

### 4. Environment Files
**Purpose**: Configuration management  
**Contains**:
- Base URL configuration
- Auth token storage
- Common variable placeholders

**When to use**: Switching between dev/staging/production

### 5. backend-api-openapi.yaml
**Purpose**: Formal API specification  
**Contains**:
- Complete API schema
- Request/response models
- Authentication schemes
- Detailed descriptions

**When to use**: API documentation, code generation, validation

---

## 🗂️ API Organization

### 11 Functional Areas

1. **Authentication** (7 endpoints)
   - User registration, login, password reset
   - JWT token management

2. **User Management** (6 endpoints)
   - User CRUD operations
   - Agent roster and assignment

3. **Position Management** (5 endpoints)
   - Role and permission management
   - Position assignment

4. **Instagram** (14 endpoints)
   - Comments, mentions, insights
   - Account management
   - Marketing events

5. **Facebook** (7 endpoints)
   - Comment management
   - Page connection and management

6. **Chats** (5 endpoints)
   - Chat listing with filters
   - Message sending
   - Assignment and read status

7. **Templates** (7 endpoints)
   - Template CRUD
   - Meta approval workflow
   - Template sending

8. **Dashboard** (1 endpoint)
   - Statistics and analytics

9. **Webhooks** (6 endpoints)
   - Instagram and Facebook webhook handlers
   - Verification endpoints

10. **Mock & Testing** (2 endpoints)
    - Mock data generation
    - Message simulation

11. **Developer** (1 endpoint)
    - Database overview

**Total**: 60+ endpoints

---

## 🚀 Getting Started Workflows

### Workflow 1: First Time User
```
1. Read README.md (5 minutes)
2. Import collection into Postman
3. Import Local environment
4. Run Login request
5. Explore other endpoints
```

### Workflow 2: Daily Developer
```
1. Keep QUICK_REFERENCE.md open
2. Use Postman collection for testing
3. Reference endpoint details as needed
```

### Workflow 3: API Integration
```
1. Review OpenAPI specification
2. Generate client code (optional)
3. Use collection for testing
4. Reference QUICK_REFERENCE for details
```

### Workflow 4: Documentation
```
1. Use OpenAPI spec for formal docs
2. Generate Swagger/Redoc UI
3. Share with team/stakeholders
```

---

## 🔧 Configuration

### Environment Variables

Both environment files include these variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `base_url` | API base URL | `http://localhost:8000` |
| `auth_token` | JWT token (auto-set) | `eyJhbGc...` |
| `user_id` | Current user ID | `uuid` |
| `chat_id` | Active chat ID | `uuid` |
| `template_id` | Template ID | `uuid` |
| `position_id` | Position ID | `uuid` |
| `ig_account_id` | Instagram account ID | `string` |
| `fb_page_id` | Facebook page ID | `string` |
| `comment_id` | Comment ID | `string` |

### Customizing Environments

1. **Local Development**
   - Edit `Backend API - Local.postman_environment.json`
   - Set `base_url` to your local server
   - Import into Postman

2. **Production**
   - Edit `Backend API - Production.postman_environment.json`
   - Set `base_url` to production URL
   - Import into Postman

3. **Custom Environment**
   - Duplicate an existing environment file
   - Modify values as needed
   - Import into Postman

---

## 🎓 Learning Path

### Beginner
1. ✅ Import collection and environment
2. ✅ Run Login request
3. ✅ Explore Authentication folder
4. ✅ Try Chat endpoints
5. ✅ Read QUICK_REFERENCE.md

### Intermediate
1. ✅ Understand all endpoint categories
2. ✅ Use filters on list endpoints
3. ✅ Work with templates
4. ✅ Connect Instagram/Facebook
5. ✅ Read full README.md

### Advanced
1. ✅ Review OpenAPI specification
2. ✅ Set up automated testing with Newman
3. ✅ Configure webhooks
4. ✅ Use WebSocket for real-time updates
5. ✅ Implement custom workflows

---

## 🧪 Testing

### Manual Testing (Postman)
```
1. Import collection
2. Select environment
3. Run requests individually
4. Check responses
```

### Automated Testing (Newman)
```bash
# Install Newman
npm install -g newman

# Run entire collection
newman run collections/Backend\ API.postman_collection.json \
  --environment environments/Backend\ API\ -\ Local.postman_environment.json

# Run specific folder
newman run collections/Backend\ API.postman_collection.json \
  --folder "Authentication" \
  --environment environments/Backend\ API\ -\ Local.postman_environment.json

# Generate HTML report
newman run collections/Backend\ API.postman_collection.json \
  --environment environments/Backend\ API\ -\ Local.postman_environment.json \
  --reporters cli,html \
  --reporter-html-export report.html
```

---

## 📊 Statistics

- **Total Endpoints**: 60+
- **Functional Areas**: 11
- **Authentication Methods**: JWT Bearer Token
- **Supported Platforms**: Instagram, Facebook
- **Webhook Endpoints**: 6
- **Admin-Only Endpoints**: ~15
- **Public Endpoints**: 8 (auth + webhooks)

---

## 🔐 Security Notes

1. **Authentication Required**: Most endpoints require Bearer token
2. **Admin Endpoints**: Clearly marked in documentation
3. **Webhook Security**: Verified by Meta's challenge mechanism
4. **Token Storage**: Use environment variables, never hardcode
5. **HTTPS**: Always use HTTPS in production

---

## 🤝 Team Collaboration

### Sharing with Team

1. **Share Collection**
   - Export from Postman
   - Share the JSON file
   - Or use Postman Team Workspace

2. **Share Documentation**
   - Share README.md and QUICK_REFERENCE.md
   - Host OpenAPI spec on internal docs
   - Generate Swagger UI for team

3. **Version Control**
   - Commit all files to Git
   - Track changes to API
   - Update documentation with API changes

---

## 📝 Maintenance

### Keeping Documentation Updated

When API changes:
1. ✅ Update Postman collection
2. ✅ Update OpenAPI specification
3. ✅ Update QUICK_REFERENCE.md
4. ✅ Update README.md if needed
5. ✅ Test all endpoints
6. ✅ Commit changes

---

## 🆘 Support & Resources

### Documentation Files
- **README.md** - Complete guide
- **QUICK_REFERENCE.md** - Quick lookup
- **INDEX.md** - This file

### External Resources
- [Postman Documentation](https://learning.postman.com/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Newman CLI](https://learning.postman.com/docs/running-collections/using-newman-cli/)

### Getting Help
- Check error messages in responses
- Review endpoint descriptions
- Check authentication setup
- Verify environment variables
- Contact: support@example.com

---

## 🎉 You're Ready!

You now have everything you need to work with the Backend API:

✅ Complete Postman collection with 60+ endpoints  
✅ OpenAPI specification for formal documentation  
✅ Environment files for easy configuration  
✅ Comprehensive guides and quick references  
✅ Testing setup with Newman  

**Next Steps**:
1. Import the collection into Postman
2. Import an environment
3. Run the Login request
4. Start exploring!

---

**Package Version**: 1.0.0  
**API Version**: 1.0.0  
**Last Updated**: 2024  
**Total Files**: 7  
**Total Endpoints**: 60+

Happy API Testing! 🚀