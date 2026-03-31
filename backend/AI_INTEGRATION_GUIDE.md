# AI Chatbot Integration Guide for UoG Navigator

## Overview
This document outlines how to integrate an AI chatbot into your University of Gondar Navigator app to answer questions about campus locations, directions, and buildings.

---

## 🔧 What You Need for AI Integration

### 1. **AI Service Provider Options**

| Provider | Pros | Cons | Cost |
|----------|------|------|------|
| **Google Gemini API** | Free tier available, good for campus data | Requires internet | Free (1M tokens/month) |
| **OpenAI GPT-4** | Most capable, excellent for conversations | Expensive | Pay-per-use |
| **Claude API** | Great for detailed explanations | Limited free tier | Free/Pay-per-use |
| **Azure OpenAI** | Enterprise-ready, secure | Complex setup | Pay-per-use |
| **Local AI (Ollama)** | No API costs, runs locally | Needs powerful device | Free |

**Recommended**: Start with **Google Gemini API** (free tier) for university campus navigation.

---

### 2. **Required Setup Steps**

#### Step 1: Get an API Key

**For Google Gemini:**
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key (keep it secret!)

**For OpenAI GPT:**
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy and secure the key

#### Step 2: Environment Variables (Backend)

Create a `.env` file in your `backend/` folder:

```env
# For Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# For OpenAI
OPENAI_API_KEY=your_openai_api_key_here
```

#### Step 3: Install Required Python Packages

```bash
pip install google-generativeai openai python-dotenv
```

---

### 3. **Knowledge Base Setup**

To make the AI understand Gondar University, you need to provide context:

#### Create a knowledge file: `backend/university_knowledge.py`

```python
UNIVERSITY_CONTEXT = """
University of Gondar Campus Information:

CAMPUSES:
1. Main Campus (Central) - Contains:
   - Administration Building
   - Main Library
   - Central Auditorium
   - Student Union Building
   - Cafeteria
   
2. Science Campus - Contains:
   - Chemistry Lab
   - Physics Lab
   - Biology Department
   - Computer Science Building
   
3. Technology Campus - Contains:
   - Engineering Building
   - Mechanical Workshop
   - Electrical Engineering Labs
   
4. Medical Campus - Contains:
   - Teaching Hospital
   - Medical School
   - Pharmacy Department

BUILDINGS AND LOCATIONS:
- Dean's Office: Main Campus, Building A
- Library: Main Campus, North Side
- Cafeteria: Main Campus, Center
- Science Labs: Science Campus, Building B
- Computer Labs: Technology Campus, 2nd Floor

FACILITIES:
- WiFi hotspots: Library, Cafeteria, Computer Labs
- Restrooms: Every building has facilities
- Emergency exits: Clearly marked in all buildings
"""

# Sample campus directions/routing info
CAMPUS_DIRECTIONS = {
    "main_to_science": "Walk south from Main Campus for 5 minutes",
    "main_to_medical": "Take the main road east for 10 minutes",
    "science_to_tech": "Walk through the garden path for 3 minutes",
}
```

---

## 📁 File Structure for AI Integration

```
backend/
├── server.py              # Main Flask server (add AI endpoints)
├── ai_service.py          # AI service handler (CREATE THIS)
├── university_knowledge.py # Campus knowledge base (CREATE THIS)
├── config.py              # Existing config
├── requirements.txt       # Add new dependencies

frontend/
├── lib/
│   ├── api_service.dart   # Add AI chat methods (MODIFY)
│   ├── ai_chat_service.dart # AI chat UI and logic (CREATE)
│   └── main.dart          # Add AI chat screen (MODIFY)
```

---

## 🎯 Implementation Plan

### Option A: Simple Q&A Bot (Beginner-Friendly)

The AI reads from your database + knowledge file and answers questions.

### Option B: RAG (Retrieval-Augmented Generation) - Advanced

The AI searches your database for relevant locations first, then generates a response.

---

## 📱 AI Features to Implement

1. **Chat Interface** - Text input where users ask questions
2. **Voice Input** - Optional speech-to-text
3. **Location-Aware Responses** - AI considers user's current location
4. **Quick Actions** - "Where is the library?", "How to get to Science Campus?"
5. **Multi-language Support** - Amharic and English

---

## 💰 Cost Estimation

| Usage Level | Monthly Cost |
|-------------|--------------|
| Light (100 users, 50 Q&A/day) | FREE (Gemini free tier) |
| Medium (500 users, 100 Q&A/day) | ~$10-20/month |
| Heavy (1000+ users) | ~$50+/month |

---

## 🚀 Quick Start Checklist

- [ ] Get API key from AI provider
- [ ] Add environment variables
- [ ] Install Python packages
- [ ] Create knowledge base file
- [ ] Add AI endpoints to server.py
- [ ] Create Flutter AI chat service
- [ ] Add chat UI to app
- [ ] Test with sample questions

---

## 📝 Example Questions the AI Should Answer

1. "Where is the Dean's office?"
2. "How do I get to the Science campus from here?"
3. "Is there a cafeteria nearby?"
4. "What buildings are in the Main campus?"
5. "Where can I find WiFi?"
6. "How do I get to the library?"
7. "Is the Medical campus open to visitors?"
8. "Where are the Computer Science labs?"

---

## 🔒 Security Considerations

1. **Never expose API keys** - Keep them in backend only
2. **Rate limiting** - Prevent spam (max 10 requests/minute/user)
3. **Input sanitization** - Filter inappropriate content
4. **Privacy** - Don't log user messages unnecessarily

---

## 📚 Resources

- Google Gemini API: https://ai.google.dev/
- OpenAI API: https://platform.openai.com/
- Flutter Speech Recognition: https://pub.dev/packages/speech_to_text

---

## Next Steps

1. See `backend/ai_service_template.py` for backend implementation
2. See `frontend/lib/ai_chat_service.dart` for Flutter implementation
3. See `frontend/lib/screens/ai_chat_screen.dart` for UI template
