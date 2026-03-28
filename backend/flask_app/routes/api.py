"""
API Routes Blueprint
Contains all mobile app API routes for locations, users, and sharing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Blueprint, jsonify, request, make_response
import json

# Import database and config
from services.database import db
from utils.config import CampusData


# Create blueprint
api_bp = Blueprint('api', __name__)


# Helper function to convert documents
def convert_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [convert_doc(d) for d in doc]
    
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            type_name = type(value).__name__
            if type_name == 'ObjectId':
                result[key] = str(value)
            elif hasattr(value, '__dict__') and isinstance(value, dict):
                result[key] = convert_doc(value)
            elif isinstance(value, list):
                result[key] = convert_doc(value)
            else:
                result[key] = value
        return result
    
    if hasattr(doc, '__class__'):
        type_name = type(doc).__name__
        if type_name == 'ObjectId':
            return str(doc)
    
    return doc


# Health check
@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    mongo_status = "connected" if db.is_connected() else "disconnected"
    
    return jsonify({
        'status': 'ok', 
        'service': 'UOG Navigator API',
        'database': {
            'mongodb': mongo_status,
            'db_name': 'uog_navigator'
        }
    })


# Get all locations
@api_bp.route('/locations', methods=['GET'])
def get_all_locations():
    """Get all campus locations from MongoDB"""
    try:
        locations = db.get_campus_locations()
        
        if not locations:
            db.initialize_default_locations()
            locations = db.get_campus_locations()
        
        db_campuses = db.get_all_campuses()
        campus_counts = db.get_building_count_by_campus()
        
        campuses_dict = {}
        for campus in db_campuses:
            campus_id = campus.get('campus_id', '')
            count = next((c['count'] for c in campus_counts if c['_id'] == campus_id), 0)
            campuses_dict[campus_id] = {
                'name': campus.get('name', ''),
                'description': campus.get('description', ''),
                'center': campus.get('center', ''),
                'count': count
            }
        
        for campus_id, campus_info in CampusData.CAMPUSES.items():
            if campus_id not in campuses_dict:
                count = next((c['count'] for c in campus_counts if c['_id'] == campus_id), 0)
                campuses_dict[campus_id] = {
                    'name': campus_info['name'],
                    'description': campus_info.get('description', ''),
                    'center': campus_info.get('center', ''),
                    'count': count
                }
        
        response_data = {
            'success': True,
            'locations': locations,
            'campuses': campuses_dict
        }
        
        response = make_response(json.dumps(response_data, default=str))
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        print(f"Error getting locations: {e}")
        response = make_response(json.dumps({'success': False, 'error': str(e)}))
        response.headers['Content-Type'] = 'application/json'
        return response, 500


# Get locations by campus
@api_bp.route('/locations/<campus_id>', methods=['GET'])
def get_locations_by_campus(campus_id):
    """Get locations for a specific campus from MongoDB"""
    locations = db.get_campus_locations(campus_id=campus_id)
    response_data = {
        'success': True,
        'campus_id': campus_id,
        'locations': locations
    }
    response = make_response(json.dumps(response_data, default=str))
    response.headers['Content-Type'] = 'application/json'
    return response


# Get locations by category
@api_bp.route('/locations/category/<category>', methods=['GET'])
def get_locations_by_category(category):
    """Get locations for a specific category from MongoDB"""
    locations = db.get_campus_locations(category=category)
    response_data = {
        'success': True,
        'category': category,
        'locations': locations
    }
    response = make_response(json.dumps(response_data, default=str))
    response.headers['Content-Type'] = 'application/json'
    return response


# Get all categories
@api_bp.route('/categories', methods=['GET'])
def get_all_categories_api():
    """Get all categories from both custom categories and campus_locations"""
    try:
        custom_cats = list(db._db.categories.find({}, {'name': 1, 'description': 1, 'icon': 1, 'color': 1}))
        custom_cat_names = [c['name'] for c in custom_cats]
        
        location_categories = db._db.campus_locations.distinct('category')
        
        all_categories = sorted(set(custom_cat_names + list(location_categories)))
        
        category_counts = {}
        for cat in all_categories:
            count = db._db.campus_locations.count_documents({'category': cat})
            category_counts[cat] = count
        
        response_data = {
            'success': True,
            'categories': all_categories,
            'counts': category_counts
        }
        response = make_response(json.dumps(response_data, default=str))
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        print(f"Error getting categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Get all campuses
@api_bp.route('/campuses', methods=['GET'])
def get_all_campuses_api():
    """Get all campuses from MongoDB"""
    try:
        db_campuses = db.get_all_campuses()
        campus_counts = db.get_building_count_by_campus()
        
        all_campuses = []
        
        for campus in db_campuses:
            campus_id = campus.get('campus_id', '')
            count = next((c['count'] for c in campus_counts if c['_id'] == campus_id), 0)
            all_campuses.append({
                'campus_id': campus_id,
                'name': campus.get('name', ''),
                'description': campus.get('description', ''),
                'center': campus.get('center', ''),
                'count': count,
                'from_db': True
            })
        
        for campus_id, campus_info in CampusData.CAMPUSES.items():
            if not any(c['campus_id'] == campus_id for c in all_campuses):
                count = next((c['count'] for c in campus_counts if c['_id'] == campus_id), 0)
                all_campuses.append({
                    'campus_id': campus_id,
                    'name': campus_info['name'],
                    'description': campus_info.get('description', ''),
                    'center': campus_info.get('center', ''),
                    'count': count,
                    'from_db': False
                })
        
        response_data = {
            'success': True,
            'campuses': all_campuses
        }
        response = make_response(json.dumps(response_data, default=str))
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        print(f"Error getting campuses: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Get all users
@api_bp.route('/users', methods=['GET'])
def get_all_users_api():
    """Get all registered users (Telegram bot users) for location sharing."""
    try:
        db.connect()
        users = db.get_all_users()
        user_list = []
        for user in users:
            user_list.append({
                'username': user.get('username', ''),
                'name': user.get('name', user.get('first_name', 'Unknown'))
            })
        return jsonify({
            'success': True,
            'users': user_list
        })
    except Exception as e:
        print(f"Error getting users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Share location to friend
@api_bp.route('/share-location', methods=['POST'])
def share_location_to_friend():
    """Share location to a friend via Telegram"""
    try:
        data = request.get_json()
        
        sender_id = data.get('sender_id')
        friend_username = data.get('friend_username', '').lower()
        coords = data.get('coords', '')
        location_name = data.get('location_name', 'Shared Location')
        
        if not sender_id or not friend_username or not coords:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Create share record
        share_id = db.create_location_share(
            sender_id=sender_id,
            sender_name=data.get('sender_name', 'Unknown'),
            friend_username=friend_username,
            coords=coords,
            location_name=location_name
        )
        
        if not share_id:
            return jsonify({
                'success': False,
                'error': 'Failed to create share record'
            }), 500
        
        # Get friend's chat_id
        friend = db.get_user(username=friend_username)
        
        return jsonify({
            'success': True,
            'share_id': share_id,
            'friend_found': friend is not None,
            'message': 'Location shared successfully'
        })
    except Exception as e:
        print(f"Error sharing location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Register app user
@api_bp.route('/register-user', methods=['POST'])
def register_app_user():
    """Register a user from the mobile app"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        username = data.get('username', '').lower()
        name = data.get('name', '')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id'
            }), 400
        
        # Add user to database (without chat_id for app users)
        result = db.add_user(
            user_id=user_id,
            username=username,
            name=name,
            chat_id=None
        )
        
        return jsonify({
            'success': result,
            'message': 'User registered successfully' if result else 'Failed to register user'
        })
    except Exception as e:
        print(f"Error registering user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Check location request
@api_bp.route('/location-request', methods=['GET'])
def check_location_request():
    """Check if there's a pending location request for this user"""
    try:
        user_id = request.args.get('user_id', type=int)
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id parameter'
            }), 400
        
        # Check pending shares (would need access to pending_shares from main app)
        # For now, just check database
        pending = db.get_pending_shares(f"user_{user_id}")
        
        return jsonify({
            'success': True,
            'has_pending': len(pending) > 0,
            'requests': pending
        })
    except Exception as e:
        print(f"Error checking location request: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Get current location
@api_bp.route('/get-current-location', methods=['GET'])
def get_current_location():
    """Get user's current stored location"""
    try:
        user_id = request.args.get('user_id', type=int)
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing user_id parameter'
            }), 400
        
        user = db.get_user(user_id=user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'location': user.get('last_location')
        })
    except Exception as e:
        print(f"Error getting current location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Update user location
@api_bp.route('/update-location', methods=['POST'])
def update_user_location():
    """Update user's GPS location"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        coords = data.get('coords', '')
        
        if not user_id or not coords:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        result = db.update_user_location(user_id, coords)
        
        return jsonify({
            'success': result,
            'message': 'Location updated successfully' if result else 'Failed to update location'
        })
    except Exception as e:
        print(f"Error updating location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Submit location (for sharing)
@api_bp.route('/submit-location', methods=['POST'])
def submit_location():
    """Submit location from app for sharing via Telegram"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        coords = data.get('coords', '')
        
        if not user_id or not coords:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Update user's location
        db.update_user_location(user_id, coords)
        
        return jsonify({
            'success': True,
            'message': 'Location submitted successfully'
        })
    except Exception as e:
        print(f"Error submitting location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Instant share location
@api_bp.route('/instant-share', methods=['POST'])
def instant_share_location():
    """Instant location sharing - send directly to friend"""
    try:
        data = request.get_json()
        
        sender_id = data.get('sender_id')
        sender_name = data.get('sender_name', 'User')
        friend_username = data.get('friend_username', '').lower()
        coords = data.get('coords', '')
        
        if not sender_id or not friend_username or not coords:
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Get friend's user record
        friend = db.get_user(username=friend_username)
        
        if not friend:
            return jsonify({
                'success': False,
                'error': 'Friend not found. They need to start the bot first.'
            }), 404
        
        # Store the share for Telegram bot to pick up
        share_id = db.create_location_share(
            sender_id=sender_id,
            sender_name=sender_name,
            friend_username=friend_username,
            coords=coords,
            location_name="Instant Share"
        )
        
        return jsonify({
            'success': True,
            'share_id': share_id,
            'message': 'Location queued for sharing'
        })
    except Exception as e:
        print(f"Error in instant share: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500