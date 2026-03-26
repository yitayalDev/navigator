# 🚀 AI Integration Setup Guide for UoG Navigator

## Quick Start - What You Need

### 1. API Key (Required)
You need an API key from one of these AI providers:

**Option A: Google Gemini (RECOMMENDED - FREE)**
1. Go to: https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

**Option B: OpenAI GPT (Pay-per-use)**
1. Go to: https://platform.openai.com/api-keys
2. Create account and add payment method
3. Create API key

### 2. Environment Setup

Create a `.env` file in your `backend/` folder:

```env
# Option 1: Google Gemini (Free)
GEMINI_API_KEY=your_gemini_api_key_here

# Option 2: OpenAI (Paid)
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Install Dependencies

```bash
# Install Python packages
pip install google-generativeai python-dotenv

# or for OpenAI
pip install openai python-dotenv
```

### 4. Update Backend Requirements

Add to `backend/requirements.txt`:
```
google-generativeai>=0.3.0
python-dotenv>=1.0.0
```

### 5. Add Routes to Your Server

Add this to your `backend/server.py`:

```python
from ai_service_template import create_ai_routes

# Call this function after creating your Flask app
create_ai_routes(app)
```

### 6. Add AI Button to Your App

In your app's navigation menu, add a button to open the AI Chat:

```dart
// In your app's main navigation
ListTile(
  leading: Icon(Icons.smart_toy),
  title: Text('Campus Assistant'),
  onTap: () {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const AIChatScreen()),
    );
  },
),
```

---

## 📁 Files Created

| File | Purpose |
|------|---------|
| `AI_INTEGRATION_GUIDE.md` | Detailed documentation |
| `backend/university_knowledge.py` | Campus information database |
| `backend/ai_service_template.py` | AI service implementation |
| `frontend/lib/ai_chat_service.dart` | Flutter API service |
| `frontend/lib/screens/ai_chat_screen.dart` | Chat UI screen |

---

## 🔧 Configuration Options

### AI Provider Selection

In `backend/ai_service_template.py`, change the provider:

```python
# For Google Gemini (free tier)
ai_assistant = AICampusAssistant(provider="gemini")

# For OpenAI (paid)
ai_assistant = AICampusAssistant(provider="openai")

# For offline keyword-based (no API needed)
ai_assistant = AICampusAssistant(provider="fallback")
```

### Customizing Campus Data

Edit `backend/university_knowledge.py` to add your actual campus information:

- Update building names
- Add real directions
- Customize facilities
- Add any Amharic translations

---

## 🧪 Testing

### Test Backend (Python)
```bash
cd backend
python ai_service_template.py
```

### Test API Endpoint
```bash
curl -X POST http://127.0.0.1:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Where is the library?"}'
```

---

## 💰 Cost Breakdown

| Provider | Free Tier | Cost After |
|----------|-----------|------------|
| **Google Gemini** | 1M tokens/month | ~$0 |
| **OpenAI GPT-3.5** | $5 free credit | ~$0.002/1K tokens |
| **Fallback Mode** | Always free | $0 |

**Recommendation**: Start with Google Gemini (free) or use fallback mode (no API needed).

---

## ❓ Troubleshooting

### "Module not found" errors
```bash
pip install -r backend/requirements.txt
```

### "API key not found" errors
1. Make sure `.env` file exists in `backend/` folder
2. Restart the backend server
3. Check the key is correctly copied

### "Connection refused" errors
1. Make sure backend is running
2. Check if port 5000 is not blocked
3. Try `http://127.0.0.1:5000` (not localhost)

### Slow responses
- Gemini: Normal, free tier has rate limits
- OpenAI: Add payment for faster responses
- Fallback: Instant, no API calls

---

## 🎯 Features Included

✅ Natural language campus questions  
✅ Directions between campuses  
✅ Building and location information  
✅ WiFi, cafeteria, library hours  
✅ Quick action buttons  
✅ Chat history  
✅ Works offline (fallback mode)  

---

## 📱 Integration with Your App

### Add to Navigation Drawer (main.dart)

```dart
Drawer(
  child: ListView(
    // ... existing items ...
    ListTile(
      leading: Icon(Icons.smart_toy_outlined),
      title: Text('Campus Assistant'),
      onTap: () {
        Navigator.pop(context);
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => AIChatScreen()),
        );
      },
    ),
  ),
)
```

### Add to Bottom Navigation

```dart
BottomNavigationBar(
  items: [
    // ... existing items ...
    BottomNavigationBarItem(
      icon: Icon(Icons.smart_toy),
      label: 'Assistant',
    ),
  ],
)
```

---

## 🎓 Customize Knowledge Base

Edit `backend/university_knowledge.py` to customize:

```python
UNIVERSITY_INFO = {
    "name": "University of Gondar",
    "campuses": [
        {
            "id": "main",
            "name": "Main Campus",
            "buildings": [
                {
                    "name": "Your Building Name",
                    "description": "Description here",
                }
            ]
        }
    ]
}
```

---

## 🌐 Multi-Language Support

To add Amharic support, update the knowledge base:

```python
UNIVERSITY_INFO_AMHARIC = {
    "welcome": "ሰላም! የዩኒቨርሲቲ ረዳት እዚህ ነው...",
    # ... more translations
}
```

---

## 📞 Need Help?

1. Read `AI_INTEGRATION_GUIDE.md` for detailed information
2. Check `backend/ai_service_template.py` comments
3. Review `frontend/lib/screens/ai_chat_screen.dart` for UI details

---

## ✅ Checklist Before Launch

- [ ] Get API key (Gemini recommended)
- [ ] Create `.env` file
- [ ] Install Python packages
- [ ] Update `requirements.txt`
- [ ] Add routes to `server.py`
- [ ] Update Flutter navigation
- [ ] Test with sample questions
- [ ] Customize campus data

---

**Ready to go!** 🎉

Start with the free Google Gemini API and switch to paid if you need more capacity.
