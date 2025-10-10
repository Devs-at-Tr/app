# Quick Start Guide - TickleGram Dashboard

This guide will help you get the Facebook Messenger integration up and running quickly.

## 🚀 Quick Setup (5 minutes)

### Step 1: Start Backend Server

```bash
cd backend
pip install -r requirements.txt
python seed_data.py
uvicorn server:app --reload --port 8000
```

The backend will start at http://localhost:8000

### Step 2: Start Frontend

```bash
cd frontend
npm install
npm start
```

The frontend will start at http://localhost:3000

### Step 3: Login & Test

1. Open http://localhost:3000
2. Login with admin credentials:
   - Email: `admin@ticklegram.com`
   - Password: `admin123`

## 🧪 Testing Facebook Integration (Mock Mode)

The app starts in **MOCK mode** by default - no Facebook App required!

### 1. Generate Test Facebook Chats

Open a new terminal and run:

```bash
# Generate 5 Facebook test chats
curl -X POST "http://localhost:8000/api/mock/generate-chats?count=5&platform=facebook" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Or use the browser console:
```javascript
fetch('http://localhost:8000/api/mock/generate-chats?count=5&platform=facebook', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
}).then(r => r.json()).then(console.log)
```

### 2. Test Platform Filtering

- Click "All Platforms" / "Instagram" / "Facebook" buttons
- Watch the chat list update
- Notice platform icons (Pink = Instagram, Blue = Facebook)

### 3. Manage Facebook Pages

- Click "Manage Facebook Pages" button
- Click "Connect New Facebook Page"
- Enter mock data:
  - **Page ID**: `mock_page_123`
  - **Page Name**: `Test Facebook Page`
  - **Access Token**: `mock_token_xyz`
- Click "Connect Page"

### 4. Send Messages

- Select a Facebook chat
- Notice the blue Facebook icon in header
- Type a message and send
- Message will be logged in mock mode

## 🔧 Switch to Real Facebook API

When ready to use actual Facebook Messenger:

### 1. Update Backend .env

```env
FACEBOOK_MODE=real
FACEBOOK_APP_ID=your_actual_facebook_app_id
FACEBOOK_APP_SECRET=your_actual_facebook_app_secret
```

### 2. Setup Facebook App

See README.md "Facebook Messenger Setup" section for detailed instructions.

### 3. Connect Real Facebook Page

- Get your Page Access Token from Facebook Developer Console
- In app, click "Manage Facebook Pages"
- Enter real Page ID and Access Token
- Messages will now send/receive via real Facebook API

## 📊 Features to Test

### Admin Features
- ✅ View all chats (Instagram + Facebook)
- ✅ Platform filtering (All/Instagram/Facebook)
- ✅ Assign chats to agents
- ✅ Manage Facebook pages
- ✅ Toggle Facebook page active status
- ✅ Dashboard stats with platform breakdown

### Agent Features
- ✅ View assigned chats only
- ✅ Send messages to both platforms
- ✅ Platform filtering on assigned chats
- ✅ Search conversations
- ✅ View platform indicators

## 🐛 Troubleshooting

### Backend won't start
- Check Python version (3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 is available

### Frontend won't start
- Check Node.js version (14+)
- Install dependencies: `npm install`
- Check port 3000 is available

### Can't see Facebook chats
- Generate mock data first
- Check platform filter is set correctly
- Refresh the page

### Mock mode not working
- Verify `FACEBOOK_MODE=mock` in backend/.env
- Restart backend server
- Check backend logs

## 📝 Next Steps

1. **Test all features** - Go through the usage guide
2. **Create Facebook App** - When ready for production
3. **Configure webhook** - Point to your production URL
4. **Deploy** - Use the migration script for production DB

## 💬 Support

If you encounter issues:
1. Check backend logs (terminal running uvicorn)
2. Check browser console for frontend errors
3. Verify environment variables are set correctly
4. Review README.md for detailed setup instructions
