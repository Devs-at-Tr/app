# Instagram DM Integration for TickleGram Dashboard

## Project Context
I have an existing Facebook Messenger management platform built with FastAPI (backend) and React (frontend) that allows teams to manage customer support through Facebook Messenger. Now extending to Instagram DMs. The system includes:

- **Backend**: FastAPI with MySQL database
- **Frontend**: React with TailwindCSS and shadcn/ui components  
- **Authentication**: JWT-based with Admin and Agent roles
- **Core Features**: Chat assignment, real-time messaging, dashboard analytics
- **Repository**: https://github.com/linkmeAman/app

## Integration Requirements

### 1. **Instagram API Integration**
- Extend the existing system to support Instagram DMs alongside Facebook Messenger
- Implement Instagram Graph API webhook integration for receiving DMs
- Add support for sending messages through Instagram Graph API
- Maintain the same chat assignment and management logic as Facebook

### 2. **Database Schema Extensions**
Models are already supporting multiple platforms (MessagePlatform Enum exists):

```python
class MessagePlatform(str, Enum):
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"

# Add Instagram-specific fields to existing models
class InstagramAccount(Base):
    id: int = Column(Integer, primary_key=True)
    instagram_account_id: str = Column(String(255))
    instagram_username: str = Column(String(255))
    access_token: str = Column(String(1024))
    connected_at: datetime = Column(DateTime)
    updated_at: datetime = Column(DateTime)
```

### 3. **Backend Implementation Tasks**

#### A. **Instagram API Integration** (`backend/instagram_api.py`)
- Create Instagram Graph API client
- Implement webhook endpoint for receiving DMs: `/webhooks/instagram`
- Add Instagram business account access token management
- Create message sending functionality through Instagram API
- Handle Instagram-specific message types (stories, posts replies, etc.)

#### B. **Extended Models** (models.py)
- Create InstagramAccount model for managing Instagram business accounts
- Ensure relationships support both Facebook and Instagram

#### C. **API Endpoints Extensions** (server.py)
- Add `/api/instagram/accounts` for managing Instagram business accounts
- Update `/api/chats/{id}/message` to handle Instagram sending
- Add `/api/instagram/webhook` for receiving Instagram DMs
- Implement Instagram story mention and post comment handling

#### D. **Authentication & Setup** (`backend/instagram_auth.py`)
- Implement Instagram business account authentication
- Add Instagram access token storage and refresh mechanism
- Create Instagram webhook verification

### 4. **Frontend Implementation Tasks**

#### A. **UI Components Extensions**
Already supporting multiple platforms, ensure:
- Instagram icon and branding in platform selector
- Instagram-specific message types display
- Instagram business account management interface

#### B. **New Components**
```jsx
// components/InstagramAccountManager.js - Manage connected Instagram accounts
// components/InstagramSetup.js - Initial Instagram integration setup
// components/InstagramMessageTypes.js - Handle Instagram-specific message types
```

#### C. **State Management**
Extend existing multi-platform state:
- Add Instagram account management state
- Add Instagram-specific message type handling
- Support Instagram story and post interactions

### 5. **Configuration & Environment**

#### Backend Environment Variables:
```env
# Instagram Config
INSTAGRAM_APP_ID=${FACEBOOK_APP_ID}  # Uses same app as Facebook
INSTAGRAM_APP_SECRET=${FACEBOOK_APP_SECRET}
INSTAGRAM_WEBHOOK_VERIFY_TOKEN=${FACEBOOK_WEBHOOK_VERIFY_TOKEN}
INSTAGRAM_API_VERSION=v18.0
```

### 6. **Implementation Phases**

#### Phase 1: Instagram API Setup
1. Configure Instagram Basic Display API
2. Set up Instagram Graph API access
3. Configure webhook subscriptions for DMs
4. Implement Instagram business account authentication

#### Phase 2: Backend Integration
1. Create Instagram API client and webhook handlers
2. Implement Instagram message sending/receiving
3. Add Instagram business account management
4. Handle Instagram-specific message types

#### Phase 3: Frontend Updates
1. Add Instagram account management interface
2. Update message display for Instagram-specific types
3. Add Instagram story and post interaction support
4. Test cross-platform functionality

### 7. **Key Technical Considerations**

- **Instagram Rate Limits**: Implement proper rate limiting for Instagram API
- **Message Types**: Handle various Instagram message types (DMs, story replies, post comments)
- **Media Handling**: Support Instagram media attachments and stories
- **Business Account**: Ensure proper Instagram business account setup
- **Cross-Platform**: Maintain consistent experience across Facebook and Instagram

### 8. **Instagram Business Account Setup Requirements**
- Instagram Professional Account required
- Connected to Facebook Page
- Instagram Graph API access configuration
- Required permissions: instagram_basic, instagram_manage_messages
- Business account conversion if needed

### 9. **Expected Deliverables**
- Full Instagram DM integration
- Instagram business account management
- Instagram-specific message type handling
- Updated documentation for Instagram setup
- Cross-platform testing coverage

### 10. **Success Criteria**
- Agents can handle Instagram DMs alongside Facebook messages
- Support for all Instagram message types
- Instagram business account management
- Consistent cross-platform experience
- Analytics include Instagram metrics

## Implementation Notes
- Leverage existing multi-platform architecture
- Maintain consistent UX across platforms
- Handle Instagram-specific features gracefully
- Document Instagram setup requirements
- Ensure MySQL optimizations for Instagram data

This integration will complete the multi-platform messaging support, allowing seamless management of both Facebook Messenger and Instagram DMs through a single interface.