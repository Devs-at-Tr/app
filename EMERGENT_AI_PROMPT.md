# Emergent AI Implementation Prompt

## Repository Information
- **GitHub Repository**: `Devs-at-Tr/app`
- **Branch**: `main`
- **Tech Stack**: React (Frontend) + FastAPI (Backend) + PostgreSQL
- **Current Status**: Fully functional multi-platform messenger management system

## Project Overview
TickleGram Dashboard is a full-stack messaging management platform for teams to handle customer support through Instagram DMs and Facebook Messenger. The system has real-time WebSocket communication, JWT authentication, role-based access (Admin/Agent), and supports both platforms with unified chat management.

---

## 🎯 PRIMARY OBJECTIVES

### Feature 1: Template Messaging System
Implement a complete template messaging feature that allows agents to send pre-approved Meta templates through both Instagram and Facebook Messenger.

### Feature 2: Mobile Responsiveness
Make the entire platform mobile-friendly with responsive design for all components, ensuring seamless experience on phones and tablets.

---

## 📋 DETAILED REQUIREMENTS

### A. Template Messaging Feature

#### Backend Requirements

1. **Database Schema Addition** (`backend/models.py`)
   - Create new model: `MessageTemplate`
   - Fields needed:
     ```python
     class MessageTemplate(Base):
         __tablename__ = "message_templates"
         
         id = Column(String(36), primary_key=True)
         name = Column(String(255), nullable=False)  # Template name
         content = Column(Text, nullable=False)  # Template message text
         category = Column(String(50), nullable=False)  # e.g., "greeting", "utility", "marketing"
         platform = Column(SQLEnum(MessagePlatform), nullable=False)  # INSTAGRAM or FACEBOOK
         meta_template_id = Column(String(255), nullable=True)  # Meta's template ID if approved
         is_meta_approved = Column(Boolean, default=False)  # Whether approved by Meta
         created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
         created_at = Column(DateTime(timezone=True), default=utc_now)
         updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
     ```

2. **API Endpoints** (`backend/server.py`)
   - `GET /templates` - Get all templates (filter by platform, category)
   - `POST /templates` - Create new template (admin only)
   - `PUT /templates/{template_id}` - Update template (admin only)
   - `DELETE /templates/{template_id}` - Delete template (admin only)
   - `POST /templates/{template_id}/send` - Send template to specific chat

3. **Template Sending Logic**
   - Integrate with existing `facebook_api.py` and `instagram_api.py`
   - Add template support to message sending functions
   - Handle Meta-approved templates with proper API calls
   - Support variable substitution if templates have placeholders (e.g., {name}, {order_id})

4. **Schema Addition** (`backend/schemas.py`)
   ```python
   class MessageTemplateCreate(BaseModel):
       name: str
       content: str
       category: str
       platform: MessagePlatform
       meta_template_id: Optional[str] = None
       is_meta_approved: bool = False

   class MessageTemplateResponse(MessageTemplateCreate):
       id: str
       created_by: str
       created_at: datetime
       updated_at: datetime
   ```

#### Frontend Requirements

1. **Template Management UI** (New Component: `frontend/src/components/TemplateManager.js`)
   - Admin-only interface for creating/editing/deleting templates
   - Form fields: name, content, category dropdown, platform selector, Meta approval checkbox
   - List view of all templates with edit/delete actions
   - Filter by platform and category
   - Add to Dashboard as new tab (only visible to admins)

2. **Template Selector in ChatWindow** (`frontend/src/components/ChatWindow.js`)
   - Add template button/icon next to the send message input
   - When clicked, show dropdown/modal with available templates
   - Filter templates by current chat's platform
   - **IMPORTANT**: Show "Utility" label/badge for Meta-approved templates (is_meta_approved === true)
   - Preview template before sending
   - Support variable substitution in UI if template has placeholders
   - Send template message on selection

3. **Template Quick Access**
   - Keyboard shortcut (e.g., Ctrl+T or Cmd+T) to open template selector
   - Search/filter templates by name or content
   - Show recent/frequently used templates first

4. **Visual Design**
   - Use existing purple accent color (#8b5cf6) for template-related UI
   - Template selector should match dark theme (#0f0f1a, #1a1a2e backgrounds)
   - "Utility" badge for Meta-approved templates: purple background with white text
   - Icons: Use lucide-react icons (e.g., `FileText`, `Send`, `CheckCircle`)

#### Implementation Details

1. **Template Categories**
   - "greeting" - Welcome messages
   - "utility" - Meta-approved transactional/utility templates
   - "marketing" - Promotional messages
   - "support" - Customer support responses
   - "closing" - Conversation closing messages

2. **Meta Template Integration**
   - Meta-approved templates must be sent using Facebook's template API
   - Templates marked as `is_meta_approved=true` should display "Utility" label
   - Ensure proper API endpoint usage for template messages vs regular messages
   - Reference: [Facebook Messenger Platform - Message Templates](https://developers.facebook.com/docs/messenger-platform/send-messages/template/generic)

3. **Variable Substitution**
   - Support placeholders: `{name}`, `{username}`, `{order_id}`, etc.
   - In UI, show input fields for variables when template is selected
   - Replace variables before sending

---

### B. Mobile Responsiveness

#### Responsive Design Requirements

1. **Breakpoints** (Use Tailwind CSS)
   ```javascript
   // Mobile: < 768px
   // Tablet: 768px - 1024px
   // Desktop: > 1024px
   ```

2. **DashboardPage Layout** (`frontend/src/pages/DashboardPage.js`)
   - **Mobile (< 768px)**:
     - Stack layout (vertical)
     - Hide sidebar by default, show as slide-out drawer with hamburger menu
     - Full-width chat window
     - Stats cards should stack vertically
     - Platform selector as bottom navigation or dropdown
   - **Tablet (768px - 1024px)**:
     - Sidebar and chat side-by-side (narrower sidebar)
     - Stats cards in 2-column grid
   - **Desktop (> 1024px)**:
     - Current layout maintained

3. **ChatSidebar** (`frontend/src/components/ChatSidebar.js`)
   - Mobile: Slide-out drawer from left, overlay on chat window
   - Add close button for mobile drawer
   - Touch-friendly tap targets (min 44x44px)
   - Swipe gestures: swipe right to open, swipe left to close

4. **ChatWindow** (`frontend/src/components/ChatWindow.js`)
   - Mobile: Full viewport height minus header
   - Message input: Fixed to bottom, always visible
   - Touch-optimized scroll for message history
   - Image attachments: Responsive sizing
   - Template selector: Bottom sheet on mobile (not dropdown)

5. **Header** (`frontend/src/components/Header.js`)
   - Mobile: 
     - Hamburger menu icon for navigation
     - Condensed user info (avatar only, name in dropdown)
     - Logout in dropdown menu
   - Desktop: Current layout

6. **StatsCards** (`frontend/src/components/StatsCards.js`)
   - Mobile: Single column, full width
   - Tablet: 2 columns
   - Desktop: 4 columns (current)

7. **Template Manager & Modals**
   - Mobile: Full-screen modal
   - Tablet/Desktop: Centered modal with backdrop

8. **Touch Interactions**
   - All buttons: minimum 44x44px touch targets
   - Swipe gestures for chat sidebar
   - Pull-to-refresh for chat list (optional)
   - Long-press for message actions (copy, forward, etc.)

#### Implementation Approach

1. **Use Tailwind Responsive Classes**
   ```jsx
   // Example
   <div className="hidden md:block">Desktop only</div>
   <div className="block md:hidden">Mobile only</div>
   <div className="flex flex-col md:flex-row">Responsive layout</div>
   ```

2. **Mobile Navigation**
   - Create `MobileNav.js` component
   - Use shadcn/ui `Sheet` component for slide-out drawer
   - Add to Header component with conditional rendering

3. **Responsive Hooks**
   - Create custom hook: `useMediaQuery.js`
   ```javascript
   export const useMediaQuery = (query) => {
     const [matches, setMatches] = useState(false);
     useEffect(() => {
       const media = window.matchMedia(query);
       if (media.matches !== matches) {
         setMatches(media.matches);
       }
       const listener = () => setMatches(media.matches);
       media.addListener(listener);
       return () => media.removeListener(listener);
     }, [matches, query]);
     return matches;
   };
   ```

4. **Mobile-Specific Components**
   - `MobileChatDrawer.js` - Drawer for chat sidebar
   - `MobileTemplateSheet.js` - Bottom sheet for template selection
   - `MobileHeader.js` - Condensed header with hamburger menu

#### Testing Requirements
- Test on real devices or browser dev tools
- Breakpoints: 375px (iPhone SE), 768px (iPad), 1024px (Desktop)
- Test touch interactions, swipe gestures, scroll behavior
- Ensure all features work on mobile (template selection, message sending, etc.)

---

## 🏗️ CODEBASE ARCHITECTURE

### File Structure
```
app/
├── backend/
│   ├── server.py              # FastAPI main server with all endpoints
│   ├── models.py              # SQLAlchemy ORM models
│   ├── schemas.py             # Pydantic schemas for request/response
│   ├── database.py            # Database configuration
│   ├── auth.py                # JWT authentication utilities
│   ├── facebook_api.py        # Facebook Messenger API integration
│   ├── instagram_api.py       # Instagram API integration
│   ├── websocket_manager.py   # WebSocket connection manager
│   └── requirements.txt       # Python dependencies
│
└── frontend/
    ├── src/
    │   ├── App.js             # Main app with routing
    │   ├── pages/
    │   │   ├── DashboardPage.js   # Main dashboard orchestrator
    │   │   ├── LoginPage.js       # Login UI
    │   │   └── SignupPage.js      # Agent signup UI
    │   ├── components/
    │   │   ├── Header.js          # Top navigation bar
    │   │   ├── StatsCards.js      # Dashboard statistics
    │   │   ├── ChatSidebar.js     # Chat list sidebar
    │   │   ├── ChatWindow.js      # Message display and input
    │   │   ├── PlatformSelector.js # Instagram/Facebook/All tabs
    │   │   └── ui/                # shadcn/ui components
    │   ├── context/
    │   │   ├── ChatContext.js     # Chat state management
    │   │   └── WebSocketContext.js # WebSocket connection
    │   └── hooks/
    │       ├── useWebSocket.js    # WebSocket custom hook
    │       └── use-toast.js       # Toast notifications
    └── package.json
```

### Key Design Patterns

1. **State Management**
   - React Context API for global state (`ChatContext`, `WebSocketContext`)
   - Local state for component-specific data
   - **CRITICAL**: Use refs for stable references to avoid infinite loops
   ```javascript
   const activePlatformRef = useRef(activePlatform);
   const loadChatsRef = useRef(loadChats);
   ```

2. **WebSocket Pattern**
   - Central WebSocket manager in `WebSocketContext`
   - Message handling in `ChatContext.handleWebSocketMessage()`
   - **IMPORTANT**: Use zero dependencies in WebSocket message handler
   ```javascript
   const handleWebSocketMessage = useCallback((message) => {
     // Use functional state updates: setChats(prev => ...)
     // Use refs instead of direct state references
   }, []); // Empty dependency array!
   ```

3. **Authentication**
   - JWT tokens stored in localStorage
   - Token sent in Authorization header: `Bearer {token}`
   - Role-based access: `user.role === 'admin'` for admin-only features

4. **Styling Conventions**
   - Dark theme: `bg-[#0f0f1a]`, `bg-[#1a1a2e]`
   - Purple accent: `#8b5cf6`
   - Tailwind CSS utility classes
   - shadcn/ui components with custom theming

### Database Models (Current)

```python
# User roles
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AGENT = "agent"

# Chat status
class ChatStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"

# Message sender types
class MessageSender(str, enum.Enum):
    AGENT = "agent"
    INSTAGRAM_USER = "instagram_user"
    FACEBOOK_USER = "facebook_user"

# Message types
class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"

# Platforms
class MessagePlatform(str, enum.Enum):
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"

# Main models: User, Chat, Message, InstagramAccount, FacebookPage
```

---

## 🎨 DESIGN GUIDELINES

### Color Palette
- Background: `#0f0f1a` (dark), `#1a1a2e` (lighter dark)
- Primary accent: `#8b5cf6` (purple)
- Text: `#ffffff` (white), `#94a3b8` (gray)
- Success: `#10b981` (green)
- Warning: `#f59e0b` (amber)
- Error: `#ef4444` (red)

### Typography
- Font: System font stack (default)
- Headings: `font-semibold` to `font-bold`
- Body: `font-normal`
- Sizes: `text-sm`, `text-base`, `text-lg`, `text-xl`

### Component Styling (Template Feature)
- Template button: Purple background `bg-purple-600 hover:bg-purple-700`
- "Utility" badge: `bg-purple-600 text-white px-2 py-1 rounded text-xs font-semibold`
- Template list items: Dark background with hover state
- Template selector modal: Match existing modal styling from shadcn/ui

### Icons
- Use `lucide-react` icons throughout
- Template icons: `FileText`, `Send`, `CheckCircle`, `Plus`
- Mobile icons: `Menu`, `X`, `ChevronLeft`, `ChevronRight`

---

## ⚠️ CRITICAL IMPLEMENTATION NOTES

### 1. Avoid Infinite Loops
- **DO NOT** add dependencies to `handleWebSocketMessage` useCallback
- Use refs for values that shouldn't trigger re-creation
- Use functional state updates: `setState(prev => ...)`
- Example:
  ```javascript
  // ❌ BAD - Will cause infinite loop
  const handleMessage = useCallback((msg) => {
    if (msg.chat_id === selectedChat.id) {
      // Do something
    }
  }, [selectedChat]); // DON'T DO THIS

  // ✅ GOOD - Use refs
  const selectedChatRef = useRef(selectedChat);
  useEffect(() => {
    selectedChatRef.current = selectedChat;
  }, [selectedChat]);

  const handleMessage = useCallback((msg) => {
    if (msg.chat_id === selectedChatRef.current?.id) {
      // Do something
    }
  }, []); // Empty dependencies!
  ```

### 2. Loading States
- Only show full-page loading on initial load (`stats === null`)
- Show component-level loading for subsequent operations
- Display error banners instead of blocking entire page

### 3. WebSocket Broadcasting
- When creating backend endpoints that modify chats/messages
- Always broadcast changes via WebSocket to all connected clients
- Pattern:
  ```python
  # After database operation
  await websocket_manager.broadcast_message({
      "type": "new_message",
      "chat_id": chat_id,
      "message": message_dict
  })
  ```

### 4. Platform Filtering
- Always respect the active platform filter (`all`, `INSTAGRAM`, `FACEBOOK`)
- When loading chats, pass platform parameter to API
- Template selector should filter by current chat's platform

### 5. Authentication
- Check `user.role === 'admin'` for admin-only features
- Template management should be admin-only
- Agents can use templates but not create/edit/delete

### 6. Error Handling
- Use try-catch blocks for all API calls
- Display user-friendly error messages with toast notifications
- Log errors to console for debugging
- Handle 401 errors by triggering logout

---

## 📝 IMPLEMENTATION CHECKLIST

### Template Messaging Feature
- [ ] Create `MessageTemplate` model in `backend/models.py`
- [ ] Add template schemas to `backend/schemas.py`
- [ ] Implement template CRUD endpoints in `backend/server.py`
- [ ] Add template sending logic to `facebook_api.py` and `instagram_api.py`
- [ ] Create `TemplateManager.js` component (admin UI)
- [ ] Add template selector to `ChatWindow.js`
- [ ] Implement "Utility" label for Meta-approved templates
- [ ] Add variable substitution support
- [ ] Test template sending on both platforms
- [ ] Add keyboard shortcut for template selector (Ctrl+T / Cmd+T)

### Mobile Responsiveness
- [ ] Create `useMediaQuery.js` custom hook
- [ ] Create `MobileChatDrawer.js` component
- [ ] Create `MobileTemplateSheet.js` component for template selection
- [ ] Update `Header.js` for mobile (hamburger menu)
- [ ] Update `DashboardPage.js` responsive layout
- [ ] Update `ChatSidebar.js` for mobile drawer
- [ ] Update `ChatWindow.js` for mobile (full height, fixed input)
- [ ] Update `StatsCards.js` responsive grid
- [ ] Add swipe gestures for chat sidebar
- [ ] Test on mobile breakpoints (375px, 768px, 1024px)
- [ ] Ensure touch targets are minimum 44x44px
- [ ] Test template selector as bottom sheet on mobile

### Testing & Validation
- [ ] Test template creation/editing/deletion (admin)
- [ ] Test template usage in chat (agents)
- [ ] Test Meta-approved template sending
- [ ] Test variable substitution
- [ ] Test mobile layout on real devices or dev tools
- [ ] Test swipe gestures
- [ ] Test responsive breakpoints
- [ ] Verify no infinite loops introduced
- [ ] Test WebSocket updates with templates
- [ ] Test all features work on mobile

---

## 🔗 USEFUL REFERENCES

### Meta/Facebook Documentation
- [Facebook Messenger Platform](https://developers.facebook.com/docs/messenger-platform/)
- [Message Templates](https://developers.facebook.com/docs/messenger-platform/send-messages/template/generic)
- [Instagram Messaging API](https://developers.facebook.com/docs/instagram-api/guides/messaging/)

### Current Project Documentation
- `README.md` - Project overview and setup
- `QUICKSTART.md` - Quick start guide
- `INSTAGRAM_INTEGRATION.md` - Instagram setup
- `FACEBOOK_WEBSOCKET_FIX.md` - Facebook WebSocket implementation
- `WEBSOCKET_INFINITE_LOOP_FIX.md` - Infinite loop fixes
- `OPTIMIZATION_CHANGES.md` - Loading optimization details

### Libraries & Frameworks
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TailwindCSS](https://tailwindcss.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [Lucide Icons](https://lucide.dev/)

---

## 🚀 GETTING STARTED

### Step 1: Clone Repository
```bash
git clone https://github.com/Devs-at-Tr/app.git
cd app
```

### Step 2: Setup Backend
```bash
cd backend
pip install -r requirements.txt
# Configure .env file (database, JWT, Facebook credentials)
python server.py  # Runs on http://localhost:8000
```

### Step 3: Setup Frontend
```bash
cd frontend
npm install
npm start  # Runs on http://localhost:3000
```

### Step 4: Create Feature Branch
```bash
git checkout -b feature/templates-and-mobile
```

### Step 5: Implementation
Follow the detailed requirements above for both features.

### Step 6: Testing
- Test template creation and usage
- Test mobile responsiveness on multiple devices
- Verify no regressions in existing features
- Test WebSocket real-time updates

### Step 7: Commit & Push
```bash
git add .
git commit -m "feat: Add template messaging and mobile responsiveness"
git push origin feature/templates-and-mobile
```

---

## 💡 ADDITIONAL NOTES

### Performance Considerations
- Lazy load templates (only fetch when template selector is opened)
- Debounce template search input
- Optimize mobile animations (use CSS transforms, avoid layout thrashing)
- Use React.memo for expensive components

### Accessibility
- Ensure keyboard navigation works for template selector
- Add ARIA labels for mobile drawer and buttons
- Ensure sufficient color contrast for "Utility" badges
- Support screen readers for template selection

### Future Enhancements (Out of Scope for Now)
- Template analytics (usage tracking)
- Template categories management
- Rich text templates with formatting
- Template approval workflow
- Template version history

---

## ✅ SUCCESS CRITERIA

### Template Messaging Feature
1. ✅ Admins can create, edit, and delete templates
2. ✅ Agents can view and use templates when sending messages
3. ✅ Meta-approved templates show "Utility" label
4. ✅ Templates filter by current chat's platform
5. ✅ Variable substitution works correctly
6. ✅ Template selector accessible via keyboard shortcut
7. ✅ Real-time updates when templates are sent
8. ✅ Templates work on both Instagram and Facebook

### Mobile Responsiveness
1. ✅ All pages render correctly on mobile (375px width)
2. ✅ Chat sidebar works as slide-out drawer on mobile
3. ✅ Touch targets are minimum 44x44px
4. ✅ Swipe gestures work for drawer open/close
5. ✅ Template selector shows as bottom sheet on mobile
6. ✅ Message input fixed to bottom on mobile
7. ✅ Stats cards stack properly on mobile
8. ✅ Navigation accessible via hamburger menu on mobile
9. ✅ All features functional on tablet (768px)
10. ✅ Smooth animations and transitions

---

## 📞 SUPPORT & QUESTIONS

If you encounter any issues or need clarification:
1. Review existing documentation files in the repo root
2. Check console logs for errors
3. Verify environment variables are configured correctly
4. Test with mock mode before real API mode
5. Ensure database migrations are up to date

---

**Good luck with the implementation! 🚀**
