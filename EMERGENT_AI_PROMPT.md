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

### Feature: Mobile Responsiveness
Make the entire platform mobile-friendly with responsive design for all components, ensuring seamless experience on phones and tablets.

---

## 📋 DETAILED REQUIREMENTS

### A. Mobile Responsiveness

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

2. **Styling Conventions**
   - Dark theme: `bg-[#0f0f1a]`, `bg-[#1a1a2e]`
   - Purple accent: `#8b5cf6`
   - Tailwind CSS utility classes
   - shadcn/ui components with custom theming
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

## 📝 IMPLEMENTATION CHECKLIST

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

---