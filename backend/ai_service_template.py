"""
AI Chat Service for University of Gondar Navigator
This module handles AI-powered chat interactions for campus information

Supports:
- AIPIPE OpenAI-compatible API (User's configuration)
- Google Gemini API
- OpenAI Direct API
- Local fallback with keyword matching
"""

import os
import re
import json
import requests
from typing import Optional, Dict, Any
from university_knowledge import (
    UNIVERSITY_INFO, 
    DIRECTIONS, 
    QUICK_ANSWERS, 
    get_knowledge_context
)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try importing AI libraries (graceful fallback if not installed)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AICampusAssistant:
    """AI Assistant for University of Gondar campus navigation and information"""
    
    def __init__(self, provider: str = "aipipe"):
        """
        Initialize the AI assistant
        
        Args:
            provider: "aipipe" (default), "gemini", "openai", or "fallback"
        """
        self.provider = provider
        self.conversation_history = []
        self.knowledge_context = get_knowledge_context()
        
        # Initialize AIPIPE (User's OpenAI-compatible API)
        if provider == "aipipe":
            self.aipipe_token = os.getenv("AIPIPE_TOKEN")
            self.aipipe_base_url = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")
            
            if self.aipipe_token:
                print("[OK] AIPIPE API configured successfully")
                self.provider = "aipipe"
            else:
                print("Warning: AIPIPE_TOKEN not found, falling back to keyword mode")
                self.provider = "fallback"
        
        # Initialize the chosen provider
        elif provider == "gemini" and GEMINI_AVAILABLE:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                print("[OK] Google Gemini API configured")
            else:
                print("Warning: GEMINI_API_KEY not found, using fallback")
                self.provider = "fallback"
                
        elif provider == "openai":
            # Direct OpenAI API (not AIPIPE)
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
            self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            
            if self.openai_api_key:
                print("[OK] OpenAI API configured")
            else:
                print("Warning: OPENAI_API_KEY not found, using fallback")
                self.provider = "fallback"
    
    def chat(self, user_message: str, user_location: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a chat message and return AI response
        
        Args:
            user_message: The user's question
            user_location: Optional user's current location {lat, lng}
            
        Returns:
            Dict with 'success', 'response', and optional 'suggestions'
        """
        try:
            # Clean and validate input
            user_message = self._clean_input(user_message)
            
            if not user_message:
                return {
                    "success": False,
                    "response": "I didn't receive a message. Could you please ask again?",
                    "suggestions": self._get_suggestions()
                }
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Generate response based on provider
            if self.provider == "aipipe":
                response = self._aipipe_chat(user_message)
            elif self.provider == "gemini":
                response = self._gemini_chat(user_message)
            elif self.provider == "openai":
                response = self._openai_chat(user_message)
            else:
                response = self._fallback_chat(user_message)
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Generate suggestions
            suggestions = self._get_suggestions()
            
            return {
                "success": True,
                "response": response,
                "suggestions": suggestions,
                "provider": self.provider
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"I encountered an issue processing your request. Please try again. Error: {str(e)}",
                "error": str(e)
            }
    
    def _gemini_chat(self, message: str) -> str:
        """Generate response using Google Gemini API"""
        try:
            prompt = f"""{self.knowledge_context}

User Question: {message}

Please provide a helpful, accurate response about the University of Gondar campus. 
Keep it concise (under 200 words) and friendly.
"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            return self._fallback_chat(message)
    
    def _aipipe_chat(self, message: str) -> str:
        """Generate response using AIPIPE OpenAI-compatible API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.aipipe_token}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""{self.knowledge_context}

User Question: {message}

Please provide a helpful, accurate response about the University of Gondar campus. 
Keep it concise (under 200 words) and friendly. Include emojis where appropriate for better UX.
"""
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful campus assistant for University of Gondar."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            # Use shorter timeout to avoid hanging - faster fallback
            response = requests.post(
                f"{self.aipipe_base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=10  # Reduced from 60 to 10 seconds for faster fallback
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"AIPIPE API error: {response.status_code} - {response.text}")
                return self._fallback_chat(message)
                
        except requests.exceptions.Timeout:
            print("AIPIPE API timeout - using fallback")
            return self._fallback_chat(message)
        except requests.exceptions.ConnectionError as e:
            print(f"AIPIPE Connection error - using fallback: {str(e)[:100]}")
            return self._fallback_chat(message)
        except Exception as e:
            print(f"AIPIPE API error: {str(e)[:100]}")
            return self._fallback_chat(message)
    
    def _openai_chat(self, message: str) -> str:
        """Generate response using OpenAI GPT API"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.knowledge_context},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message['content']
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._fallback_chat(message)
    
    def _fallback_chat(self, message: str) -> str:
        """
        Fallback keyword-based response system
        Used when API is not available
        """
        message_lower = message.lower()
        
        # Check for location queries
        if any(word in message_lower for word in ['where', 'location', 'find', 'located', 'building', 'room']):
            return self._handle_location_query(message_lower)
        
        # Check for directions queries
        elif any(word in message_lower for word in ['how to get', 'directions', 'route', 'path', 'walk', 'go to']):
            return self._handle_directions_query(message_lower)
        
        # Check for facilities queries
        elif any(word in message_lower for word in ['wifi', 'restroom', 'toilet', 'parking', 'food', 'cafeteria']):
            return self._handle_facility_query(message_lower)
        
        # Check for hours/times
        elif any(word in message_lower for word in ['hours', 'open', 'close', 'time', 'when']):
            return self._handle_hours_query(message_lower)
        
        # Check for campus information
        elif any(word in message_lower for word in ['campus', 'main', 'science', 'technology', 'medical']):
            return self._handle_campus_query(message_lower)
        
        # Default response
        else:
            return self._get_default_response(message_lower)
    
    def _handle_location_query(self, query: str) -> str:
        """Handle 'where is' type queries"""
        locations = {
            'dean': 'The Deans Office is located in the Administration Building, Main Campus, 2nd Floor',
            'library': 'The Main Library is in the Main Campus, North Side. It has 3 floors with study rooms and computer stations.',
            'cafeteria': 'The Main Cafeteria is in the Main Campus, Center area. Open 7AM-8PM daily.',
            'admin': 'Administration Building is in the Main Campus, near the main entrance.',
            'computer': 'Computer Science labs are in the Science Campus, 2nd Floor of the CS Building.',
            'hospital': 'The Teaching Hospital is in the Medical Campus. Open 24/7 for emergencies.',
            'auditorium': 'The Central Auditorium is in Main Campus, west side. Used for ceremonies.',
            'wifi': 'WiFi is available at: Library, Cafeteria, Admin Building, and CS Building.'
        }
        
        for keyword, response in locations.items():
            if keyword in query:
                return response
        
        return "Could you specify which location you're looking for? We have buildings across Main, Science, Technology, and Medical campuses."
    
    def _handle_directions_query(self, query: str) -> str:
        """Handle directions queries"""
        # Check specific routes
        for route_key, route_info in DIRECTIONS.items():
            if route_key.replace('_', ' ') in query:
                return f"To get from {route_info['start']} to {route_info['end']}:\n{route_info['instructions']}\n\n⏱️ Estimated time: {route_info['duration']}"
        
        # General direction help
        return """I can help with directions! Here are common routes:

• Main → Science Campus: 5 min walk, south gate
• Main → Technology Campus: 10 min walk, east side
• Main → Medical Campus: 15 min walk, follow hospital signs
• Library → Cafeteria: 2 min walk, across the courtyard

Could you tell me where you're starting from and where you want to go?"""
    
    def _handle_facility_query(self, query: str) -> str:
        """Handle facility queries"""
        if 'wifi' in query:
            return """[WIFI] WiFi is available at these locations:
- Main Library (strongest signal)
- Main Cafeteria
- Administration Building
- Computer Science Building
- Student Union Building

Login: UoG_Student
Password: Your student ID number"""
        
        elif 'restroom' in query or 'toilet' in query:
            return "[RESTROOM] Restrooms are available on every floor of all campus buildings. They're clearly marked with signs."
        
        elif 'cafeteria' in query or 'food' in query or 'eat' in query:
            return """[CAFETERIA] Main Cafeteria (Main Campus, Center):
- Breakfast: 7:00 AM - 9:00 AM
- Lunch: 12:00 PM - 2:00 PM
- Dinner: 6:00 PM - 8:00 PM

Coffee and snacks available all day!"""
        
        elif 'parking' in query:
            return "[PARKING] Main parking area is near the Technology Campus entrance. Free for students."
        
        return "Could you specify which facility you're asking about?"
    
    def _handle_hours_query(self, query: str) -> str:
        """Handle hours/time queries"""
        return """[HOURS] Campus Hours:

- Library: Mon-Fri 7AM-10PM, Weekends 8AM-6PM
- Cafeteria: 7AM-8PM daily
- Admin Office: Mon-Fri 8AM-5PM
- All Buildings: Generally 6AM-10PM

Emergency services available 24/7."""
    
    def _handle_campus_query(self, query: str) -> str:
        """Handle campus information queries"""
        campuses_info = {
            'main': """[MAIN CAMPUS] Central Campus
Buildings: Admin, Library, Auditorium, Cafeteria, Student Union
Best for: Administrative tasks, studying, dining""",
            
            'science': """[SCIENCE CAMPUS] Sciences Campus
Buildings: Chemistry, Physics, Biology, Computer Science
Best for: Lab work, research, computing""",
            
            'technology': """[TECHNOLOGY CAMPUS] Engineering Campus
Buildings: Engineering, Mechanical Workshop, Electrical
Best for: Engineering students, hands-on training""",
            
            'medical': """[MEDICAL CAMPUS] Health Sciences Campus
Buildings: Teaching Hospital, Medical School, Pharmacy
Best for: Medical/health students, emergencies"""
        }
        
        for campus_key, info in campuses_info.items():
            if campus_key in query:
                return info
        
        return """[CAMPUS INFO] University of Gondar has 4 campuses:
1. Main Campus - Admin & General
2. Science Campus - Sciences & Computing
3. Technology Campus - Engineering
4. Medical Campus - Health Sciences

Which campus would you like to know more about?"""
    
    def _get_default_response(self, query: str) -> str:
        """Get default response with suggestions"""
        return """I'm here to help you navigate the University of Gondar! 

You can ask me about:
- "Where is the library?"
- "How do I get to Science Campus?"
- "Where can I find WiFi?"
- "What are the library hours?"
- "Tell me about the Medical Campus"

What would you like to know?"""
    
    def _clean_input(self, text: str) -> str:
        """Clean and validate user input"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove potentially harmful characters
        text = re.sub(r'[^\w\s\?\.\,\!\-\'\"]', '', text)
        # Limit length
        if len(text) > 500:
            text = text[:500]
        return text.strip()
    
    def _get_suggestions(self) -> list:
        """Get suggested questions for quick actions"""
        return [
            "Where is the library?",
            "How to get to Science Campus?",
            "What are the cafeteria hours?",
            "Where can I find WiFi?",
            "Tell me about the Medical Campus"
        ]
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []


# Flask route helper (add to your server.py)
def create_ai_routes(app):
    """Create AI-related routes for Flask app"""
    from flask import request, jsonify
    
    # Initialize AI assistant with AIPIPE (using user's API)
    ai_assistant = AICampusAssistant(provider="aipipe")  # Default to user's AIPIPE API
    
    @app.route('/api/ai/chat', methods=['POST'])
    def ai_chat():
        """Main AI chat endpoint"""
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        user_message = data['message']
        user_location = data.get('location')  # Optional {lat, lng}
        
        result = ai_assistant.chat(user_message, user_location)
        
        return jsonify(result)
    
    @app.route('/api/ai/suggestions', methods=['GET'])
    def ai_suggestions():
        """Get suggested questions"""
        return jsonify({
            'success': True,
            'suggestions': ai_assistant._get_suggestions()
        })
    
    @app.route('/api/ai/clear', methods=['POST'])
    def ai_clear():
        """Clear conversation history"""
        ai_assistant.clear_history()
        return jsonify({
            'success': True,
            'message': 'Conversation cleared'
        })


# Example usage
if __name__ == "__main__":
    # Test the assistant (uses AIPIPE by default)
    assistant = AICampusAssistant(provider="aipipe")
    
    print("UoG Campus Assistant (AIPIPE Mode)")
    print("=" * 50)
    
    test_questions = [
        "Where is the library?",
        "How do I get to Science Campus from Main?",
        "Where can I find WiFi?",
        "What are the cafeteria hours?",
        "Tell me about the Medical Campus"
    ]
    
    for question in test_questions:
        print(f"\nQ: {question}")
        response = assistant.chat(question)
        print(f"A: {response['response']}")
        print("-" * 50)
