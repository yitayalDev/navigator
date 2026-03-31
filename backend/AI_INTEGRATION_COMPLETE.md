# AI Integration Complete Guide for UoG Navigator

## ✅ What's Already Created

### Backend Files:
- `backend/ai_server.py` - Advanced AI server with RAG (Retrieval-Augmented Generation)
- `backend/.env` - Environment configuration template
- `backend/requirements.txt` - Python dependencies

### Frontend Files:
- `frontend/lib/ai_chat_service.dart` - Flutter AI service client
- `frontend/lib/screens/ai_chat_screen.dart` - Chat UI screen

---

## 📋 Complete Requirements Checklist

### 1. API Key for AI (REQUIRED)

Choose one AI provider:

| Provider | Cost | Quality | Sign Up |
|----------|------|---------|---------|
| **AIPIPE** (Recommended) | Free tier | Good | https://aipipe.org |
| **OpenAI** | Pay-as-you-go | Best | https://platform.openai.com |
| **Groq** | Free tier | Very Good | https://console.groq.com |

**For AIPIPE Setup:**
1. Sign up at https://aipipe.org
2. Get your API key
3. Add to `backend/.env`:
```
AIPIPE_TOKEN=your_aipipe_token_here
OPENAI_BASE_URL=https://aipipe.org/openai/v1
```

### 2. MongoDB Database (RECOMMENDED)

**Install Options:**
- **Local:** Download from https://www.mongodb.com/try/download/community
- **Cloud:** Use MongoDB Atlas free tier at https://www.mongodb.com/cloud/atlas

**Connection in `backend/.env`:**
```
MONGO_URI=mongodb://localhost:27017
MONGO_DB=uog_navigator
```

### 3. Python Dependencies

**Install:**
```bash
cd backend
pip install -r requirements.txt
```

Required packages in `requirements.txt`:
- flask>=2.0
- flask-cors>=3.0
- requests>=2.25
- python-dotenv>=0.19
- pymongo>=4.0

---

## 🚀 Quick Start Steps

### Step 1: Get AIPIPE API Key
1. Go to https://aipipe.org
2. Sign up and get free API key
3. Edit `backend/.env` and add your token

### Step 2: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Start AI Server
```bash
cd backend
python ai_server.py
```

### Step 4: Update Frontend IP
Edit `frontend/lib/ai_chat_service.dart`:
```dart
static const String baseUrl = 'http://YOUR_COMPUTER_IP:5001';
```

Edit `frontend/lib/api_service.dart`:
```dart
static const String baseUrl = 'http://YOUR_COMPUTER_IP:5000';
```

### Step 5: Build Flutter App
```bash
cd frontend
flutter build apk --debug
```

### Step 6: Install on Phone
Transfer APK to phone and install.

---

## 🎯 What the AI Can Answer

The AI can answer questions about:

### Campus Information
- "Where is the Tewodros campus?"
- "Tell me about Maraki campus"
- "What buildings are in Fasil campus?"

### Directions & Navigation
- "How do I get from the library to the cafeteria?"
- "Where is the nearest WiFi?"
- "How to reach the Science labs?"

### Facilities
- "What dining options are available?"
- "Where can I find computer labs?"
- "Tell me about dormitories"
- "Where is the university clinic?"

### General
- "What are the campus hours?"
- "Where is administration?"
- "Tell me about university facilities"

---

## 🔧 Server Endpoints

AI Server runs on port **5001**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai/chat` | POST | Send message to AI |
| `/api/ai/suggestions` | GET | Get suggested questions |
| `/api/ai/campuses` | GET | Get all campuses |
| `/api/ai/clear` | POST | Clear conversation |
| `/health` | GET | Health check |

---

## ❓ FAQ

### Q: Can I use AI without MongoDB?
**A:** Yes! The AI has a fallback keyword system. It will work without MongoDB, but MongoDB gives much better responses using RAG.

### Q: Does the AI work offline?
**A:** No, it needs internet for AI API calls. The fallback works offline.

### Q: How accurate is the AI?
**A:** Very accurate with MongoDB connected. RAG queries your campus database for real information.

### Q: Can I customize responses?
**A:** Yes! Edit `system_prompt` in `ai_server.py` (around line 194-208).

---

## 📱 App Features

The AI chat screen includes:
- Real-time chat interface
- Typing indicators
- Suggested questions
- Location-aware responses
- Quick action buttons

---

## ✅ Summary - All Things You Need:

| Item | Status | Where to Get |
|------|--------|--------------|
| AIPIPE Token | **Required** | https://aipipe.org |
| MongoDB | Recommended | Local install or Atlas |
| Python packages | Required | `pip install -r requirements.txt` |
| Computer IP | Required | Check with `ipconfig` |
| AndroidManifest | ✅ Done | Already configured |

---

## 🔗 File Reference

| File | Purpose |
|------|---------|
| `backend/ai_server.py` | AI server with RAG |
| `backend/.env` | API keys config |
| `backend/requirements.txt` | Python packages |
| `frontend/lib/ai_chat_service.dart` | Flutter AI client |
| `frontend/lib/screens/ai_chat_screen.dart` | Chat UI |

---

**Your AI integration is ready!** Get an AIPIPE token and start the server to begin using the AI assistant in your app.
