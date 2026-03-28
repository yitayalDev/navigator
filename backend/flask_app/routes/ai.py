"""
AI Chat Routes Blueprint
Contains AI assistant endpoints for campus navigation chat
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Blueprint, jsonify, request


# Create blueprint
ai_bp = Blueprint('ai', __name__)


# Global AI assistant instance (will be set from main app)
ai_assistant = None


def set_ai_assistant(assistant):
    """Set the AI assistant from the main app"""
    global ai_assistant
    ai_assistant = assistant


# AI Chat endpoint
@ai_bp.route('/chat', methods=['POST'])
def ai_chat():
    """Main AI chat endpoint for campus assistant"""
    global ai_assistant
    
    if ai_assistant is None:
        # Try to reinitialize
        try:
            from ai_service_template import AICampusAssistant
            ai_assistant = AICampusAssistant(provider="aipipe")
        except Exception as e:
            print(f"Failed to reinitialize AI: {e}")
            return jsonify({
                'success': False,
                'error': 'AI Assistant not available',
                'details': str(e)
            }), 500
    
    if ai_assistant.provider == "fallback":
        print("[DEBUG] AI using fallback mode - local keyword responses")
    else:
        print(f"[DEBUG] AI using provider: {ai_assistant.provider}")
    
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        user_message = data['message']
        user_location = data.get('location')  # Optional {lat, lng}
        
        print(f"[DEBUG] Processing message: {user_message[:50]}...")
        result = ai_assistant.chat(user_message, user_location)
        
        print(f"[DEBUG] AI response generated, success: {result.get('success')}")
        return jsonify(result)
        
    except Exception as e:
        print(f"[ERROR] Error in ai_chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'response': 'Sorry, I encountered an error. Please try again.'
        }), 500


# AI Health check
@ai_bp.route('/health', methods=['GET'])
def ai_health():
    """Health check for AI endpoint - useful for debugging connectivity"""
    status = {
        'status': 'ok',
        'ai_available': ai_assistant is not None,
        'provider': ai_assistant.provider if ai_assistant else 'none',
        'token_available': bool(ai_assistant.aipipe_token) if ai_assistant and hasattr(ai_assistant, 'aipipe_token') else False
    }
    
    return jsonify(status)


# AI Suggestions
@ai_bp.route('/suggestions', methods=['GET'])
def ai_suggestions():
    """Get suggested questions for quick actions"""
    if ai_assistant is None:
        return jsonify({
            'success': False,
            'suggestions': [
                "Where is the library?",
                "How to get to Science Campus?",
                "What are the cafeteria hours?",
                "Where can I find WiFi?"
            ]
        })
    
    return jsonify({
        'success': True,
        'suggestions': ai_assistant._get_suggestions()
    })


# Clear conversation history
@ai_bp.route('/clear', methods=['POST'])
def ai_clear():
    """Clear conversation history"""
    if ai_assistant is None:
        return jsonify({
            'success': False,
            'error': 'AI Assistant not available'
        }), 500
    
    ai_assistant.clear_history()
    return jsonify({
        'success': True,
        'message': 'Conversation cleared'
    })