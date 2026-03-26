"""
Advanced AI Chat Server with RAG (Retrieval-Augmented Generation)
University of Gondar Navigator - Uses MongoDB data + AIPIPE API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import requests

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

# Check for AIPIPE token
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
AIPIPE_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")

if AIPIPE_TOKEN:
    print("[OK] AIPIPE API configured")
else:
    print("[WARN] AIPIPE_TOKEN not found - using enhanced fallback")

# MongoDB Connection
try:
    from pymongo import MongoClient
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "uog_navigator")
    
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # Test connection
    db = mongo_client[MONGO_DB]
    print("[OK] MongoDB connected")
    MONGODB_AVAILABLE = True
except Exception as e:
    print(f"[WARN] MongoDB not available: {e}")
    MONGODB_AVAILABLE = False
    db = None

def get_locations_from_db(query: str = None, campus: str = None, category: str = None):
    """Get locations from MongoDB"""
    if not MONGODB_AVAILABLE or db is None:
        return []
    
    try:
        mongo_query = {}
        
        if campus:
            mongo_query['campus'] = campus.lower()
        
        if category:
            mongo_query['category'] = category.lower()
        
        if query:
            # Search in name and description
            mongo_query['$or'] = [
                {'name': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}}
            ]
        
        locations = list(db.campus_locations.find(mongo_query, {'_id': 0}).limit(20))
        return locations
    except Exception as e:
        print(f"MongoDB query error: {e}")
        return []

def get_all_campuses():
    """Get all campuses from MongoDB"""
    if not MONGODB_AVAILABLE or db is None:
        return []
    
    try:
        campuses = list(db.campus_locations.distinct('campus'))
        return campuses
    except:
        return []

def get_campus_info(campus_name: str):
    """Get all locations in a specific campus"""
    return get_locations_from_db(campus=campus_name)

def format_locations_for_ai(locations: list) -> str:
    """Format locations into readable text for AI"""
    if not locations:
        return "No specific locations found."
    
    formatted = []
    
    # Group by campus
    by_campus = {}
    for loc in locations:
        campus = loc.get('campus', 'unknown').upper()
        if campus not in by_campus:
            by_campus[campus] = []
        by_campus[campus].append(loc)
    
    for campus, locs in by_campus.items():
        formatted.append(f"\n=== {campus} CAMPUS ===")
        
        # Group by category
        by_category = {}
        for loc in locs:
            cat = loc.get('category', 'other').replace('_', ' ').title()
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(loc)
        
        for cat, cat_locs in by_category.items():
            formatted.append(f"\n[{cat}s]:")
            for loc in cat_locs:
                name = loc.get('name', 'Unknown')
                desc = loc.get('description', '')
                coords = loc.get('coords', '')
                formatted.append(f"  - {name}: {desc} (Coords: {coords})")
    
    return "\n".join(formatted)

def build_context_from_db(user_query: str) -> str:
    """Build context by querying MongoDB based on user question"""
    
    # Extract keywords from query
    query_lower = user_query.lower()
    
    locations = []
    
    # Check for campus mentions
    campuses = get_all_campuses()
    mentioned_campuses = []
    for campus in campuses:
        if campus.lower() in query_lower:
            mentioned_campuses.append(campus)
    
    # Check for category mentions
    categories = ['library', 'cafe', 'lab', 'building', 'administration', 'dorm', 'dormitory', 
                  'lecture', 'classroom', 'clinic', 'hospital', 'store', 'stadium', 'animal']
    mentioned_categories = []
    for cat in categories:
        if cat in query_lower:
            mentioned_categories.append(cat)
    
    # Search based on keywords
    if mentioned_campuses and mentioned_categories:
        # Specific campus + specific category
        for campus in mentioned_campuses:
            for cat in mentioned_categories:
                locations.extend(get_locations_from_db(campus=campus, category=cat))
    elif mentioned_campuses:
        # Just campus mentioned - get all from that campus
        for campus in mentioned_campuses:
            locations.extend(get_locations_from_db(campus=campus))
    elif mentioned_categories:
        # Just category mentioned
        for cat in mentioned_categories:
            locations.extend(get_locations_from_db(category=cat))
            # Also try plurals
            if cat.endswith('s'):
                locations.extend(get_locations_from_db(category=cat[:-1]))
            else:
                locations.extend(get_locations_from_db(category=cat + 's'))
    else:
        # General query - search in names and descriptions
        search_terms = re.findall(r'\b\w+\b', query_lower)
        search_terms = [t for t in search_terms if len(t) > 3]  # Skip short words
        
        for term in search_terms[:5]:  # Limit to 5 terms
            results = get_locations_from_db(query=term)
            locations.extend(results)
    
    # Remove duplicates
    seen = set()
    unique_locations = []
    for loc in locations:
        key = loc.get('name', '')
        if key not in seen:
            seen.add(key)
            unique_locations.append(loc)
    
    return format_locations_for_ai(unique_locations)

def generate_ai_response(user_query: str, db_context: str) -> str:
    """Generate AI response using AIPIPE API with database context"""
    
    if not AIPIPE_TOKEN:
        return generate_fallback_response(user_query, db_context)
    
    try:
        system_prompt = f"""You are a helpful AI assistant for University of Gondar campus navigation.

CAMPUS INFORMATION (from database):
{db_context}

RULES:
1. Answer questions about campus locations, buildings, facilities, directions
2. Use the database information above to provide accurate details
3. Include building names, descriptions, and coordinates when available
4. Be helpful, friendly, and concise
5. If information is not in the database, say you don't have that specific info
6. Provide directions using landmarks when possible
7. Mention campus names: Tewodros, Maraki, Fasil

Answer the user's question based on the database information provided."""

        headers = {
            "Authorization": f"Bearer {AIPIPE_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{AIPIPE_BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            print(f"AIPIPE error: {response.status_code}")
            return generate_fallback_response(user_query, db_context)
            
    except requests.exceptions.Timeout:
        print("AIPIPE timeout")
        return generate_fallback_response(user_query, db_context)
    except requests.exceptions.ConnectionError:
        print("AIPIPE connection error")
        return generate_fallback_response(user_query, db_context)
    except Exception as e:
        print(f"AIPIPE error: {e}")
        return generate_fallback_response(user_query, db_context)

def generate_fallback_response(user_query: str, db_context: str) -> str:
    """Fallback response when API is not available - uses MongoDB data"""
    
    query = user_query.lower()
    
    # If we have database context, use it
    if db_context and "No specific locations found" not in db_context:
        return f"Based on the University of Gondar database:\n\n{db_context}\n\nIs there anything specific you'd like to know about these locations?"
    
    # Keyword-based responses
    if 'library' in query:
        return "The University of Gondar has several libraries across campuses:\n" + \
               "- Post Library (Tewodros Campus)\n" + \
               "- T15 Library (Tewodros Campus)\n" + \
               "- Veterinary Library (Tewodros Campus)\n\n" + \
               "Libraries are open during regular campus hours (7AM-10PM)."
    
    elif 'cafeteria' in query or 'cafe' in query or 'food' in query:
        return "Campus dining options:\n" + \
               "- Main Cafeteria (Tewodros Campus)\n" + \
               "- Cafe Store (Tewodros Campus)\n" + \
               "- Addis Hiywot Cafe (Tewodros Campus)\n" + \
               "- T-Lounge (Tewodros Campus)\n" + \
               "- Aman Lounge (Tewodros Campus)\n\n" + \
               "Cafeteria hours: 7AM-8PM daily"
    
    elif 'lab' in query or 'computer' in query:
        return "Computer and science labs available:\n" + \
               "- T9 Computer Lab (Tewodros)\n" + \
               "- T10 Lab (Tewodros)\n" + \
               "- Biology Lab (Tewodros)\n" + \
               "- Chemistry Lab (Tewodros)\n" + \
               "- Physics Lab (Tewodros)\n" + \
               "- Info Science Lab (Tewodros)\n" + \
               "- Veterinary Lab (Tewodros)\n\n" + \
               "Labs require student ID for access."
    
    elif 'tewodros' in query:
        return "Tewodros Campus features:\n" + \
               "- President Office 1 & 2\n" + \
               "- Main Registrar\n" + \
               "- Multiple Lecture Halls (T11-T35)\n" + \
               "- Computer & Science Labs\n" + \
               "- Libraries\n" + \
               "- Cafeterias\n" + \
               "- University Clinic\n" + \
               "- Stadium\n" + \
               "- Dormitories"
    
    elif 'maraki' in query:
        return "Maraki Campus is one of the main campuses of University of Gondar. " + \
               "It houses administrative offices and academic buildings. " + \
               "The main gate is located at the entrance."
    
    elif 'fasil' in query:
        return "Fasil Campus is dedicated to specialized studies. " + \
               "Please check with the administration for specific building locations."
    
    elif 'dorm' in query or 'dormitory' in query or 'hostel' in query:
        return "Student dormitories available:\n" + \
               "- Federal Dormitory (Tewodros Campus)\n" + \
               "- Prep Dormitory (Tewodros Campus)\n\n" + \
               "Contact the student affairs office for accommodation inquiries."
    
    elif 'directions' in query or 'where' in query or 'how to get' in query:
        return "To help with directions, please tell me:\n" + \
               "1. Your starting location\n" + \
               "2. Where you want to go\n\n" + \
               "The campuses are:\n" + \
               "- Tewodros (Main Campus with Admin)\n" + \
               "- Maraki\n" + \
               "- Fasil"
    
    else:
        return f"""I'm here to help you navigate University of Gondar!

Ask me about:
- Locations (libraries, labs, cafes, buildings)
- Campuses (Tewodros, Maraki, Fasil)
- Directions between locations
- Building descriptions

Available data: {len(get_all_campuses())} campuses with buildings, libraries, labs, cafes, and more.

What would you like to know?"""

# API Endpoints
@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Main AI chat endpoint with RAG"""
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({
            'success': False,
            'error': 'Message is required'
        }), 400
    
    user_message = data['message']
    
    # Get context from MongoDB
    db_context = build_context_from_db(user_message)
    
    # Generate response
    response = generate_ai_response(user_message, db_context)
    
    return jsonify({
        'success': True,
        'response': response,
        'db_context': db_context if db_context and "No specific" not in db_context else None,
        'suggestions': [
            "Where is the library in Tewodros?",
            "What cafes are on campus?",
            "How do I get to Maraki from Tewodros?",
            "Where can I find computer labs?",
            "Tell me about dormitories"
        ],
        'provider': 'aipipe_rag' if AIPIPE_TOKEN else 'fallback_rag'
    })

@app.route('/api/ai/suggestions', methods=['GET'])
def ai_suggestions():
    """Get suggested questions"""
    return jsonify({
        'success': True,
        'suggestions': [
            "Where is the library?",
            "What cafes are on Tewodros campus?",
            "How to get to Maraki from Tewodros?",
            "Where can I find computer labs?",
            "Tell me about dormitories",
            "What buildings are in Tewodros?",
            "Where is the cafeteria?",
            "Is there a hospital on campus?"
        ]
    })

@app.route('/api/ai/clear', methods=['POST'])
def ai_clear():
    """Clear conversation (no-op in stateless mode)"""
    return jsonify({
        'success': True,
        'message': 'Conversation cleared'
    })

@app.route('/api/ai/campuses', methods=['GET'])
def get_campuses():
    """Get all campuses with location counts"""
    if not MONGODB_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'MongoDB not available'
        }), 500
    
    try:
        campuses = list(db.campus_locations.aggregate([
            {'$group': {'_id': '$campus', 'count': {'$sum': 1}}}
        ]))
        
        return jsonify({
            'success': True,
            'campuses': [{'name': c['_id'], 'location_count': c['count']} for c in campuses]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'ai_provider': 'aipipe_rag' if AIPIPE_TOKEN else 'fallback_rag',
        'mongodb_available': MONGODB_AVAILABLE,
        'features': ['chat', 'suggestions', 'campuses']
    })

if __name__ == '__main__':
    print("=" * 60)
    print("UoG Navigator - Advanced AI Chat Server (RAG)")
    print("=" * 60)
    print(f"AI Provider: {'AIPIPE + MongoDB RAG' if AIPIPE_TOKEN else 'MongoDB Fallback'}")
    print(f"MongoDB: {'Connected' if MONGODB_AVAILABLE else 'Not available'}")
    print()
    print("Starting server on http://127.0.0.1:5001")
    print("API Endpoints:")
    print("  POST /api/ai/chat - AI chat with RAG")
    print("  GET  /api/ai/suggestions - Get suggestions")
    print("  GET  /api/ai/campuses - Get all campuses")
    print("  POST /api/ai/clear - Clear history")
    print("  GET  /health - Health check")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
