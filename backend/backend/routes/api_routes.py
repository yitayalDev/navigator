"""
API Routes Module
Handles all REST API endpoints for the mobile app
"""
from flask import jsonify, request
import logging

logger = logging.getLogger(__name__)


def register_api_routes(app, db):
    """Register API routes with the Flask app."""
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'UOG Navigator API',
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
    
    @app.route('/api/locations', methods=['GET'])
    def get_all_locations():
        """Get all locations."""
        try:
            campus_id = request.args.get('campus_id')
            if campus_id:
                locations = db.get_locations_by_campus(campus_id)
            else:
                locations = db.get_all_locations()
            
            return jsonify({
                'success': True,
                'locations': locations
            })
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            response = app.make_response(jsonify({'success': False, 'error': str(e)}))
            response.headers['Content-Type'] = 'application/json'
            return response, 500
    
    @app.route('/api/locations/<campus_id>', methods=['GET'])
    def get_locations_by_campus(campus_id):
        """Get locations for a specific campus."""
        try:
            locations = db.get_locations_by_campus(campus_id)
            return jsonify({
                'success': True,
                'campus_id': campus_id,
                'count': len(locations),
                'locations': locations
            })
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/locations/category/<category>', methods=['GET'])
    def get_locations_by_category(category):
        """Get locations filtered by category."""
        try:
            locations = db.get_locations_by_category(category)
            return jsonify({
                'success': True,
                'category': category,
                'count': len(locations),
                'locations': locations
            })
        except Exception as e:
            logger.error(f"Error getting locations by category: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/categories', methods=['GET'])
    def get_all_categories_api():
        """Get all categories."""
        try:
            categories = db.get_all_categories()
            return jsonify({
                'success': True,
                'categories': categories
            })
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/campuses', methods=['GET'])
    def get_all_campuses_api():
        """Get all campuses."""
        try:
            campuses = db.get_all_campuses()
            return jsonify({
                'success': True,
                'campuses': campuses
            })
        except Exception as e:
            logger.error(f"Error getting campuses: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/users', methods=['GET'])
    def get_all_users_api():
        """Get all users."""
        try:
            users = db.get_all_users()
            # Don't return passwords
            safe_users = [{'user_id': u.get('user_id'), 'username': u.get('username'), 
                          'name': u.get('name'), 'created_at': u.get('created_at')} 
                         for u in users]
            return jsonify({
                'success': True,
                'count': len(safe_users),
                'users': safe_users
            })
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/share-location', methods=['POST'])
    def share_location_to_friend():
        """Share user's current location to a friend via Telegram."""
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            friend_username = data.get('friend_username')
            
            if not user_id or not friend_username:
                return jsonify({
                    'success': False,
                    'error': 'Missing user_id or username parameter'
                }), 400
            
            # Get current location
            user = db.get_user(user_id=user_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Get friend's chat_id
            friend = db.get_user(username=friend_username.lower())
            if not friend:
                return jsonify({
                    'success': False,
                    'error': 'Friend not found. They need to start the bot first.'
                }), 404
            
            return jsonify({
                'success': True,
                'message': 'Location share initiated',
                'friend_chat_id': friend.get('chat_id')
            })
        except Exception as e:
            logger.error(f"Error sharing location: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/register-user', methods=['POST'])
    def register_app_user():
        """Register a user from the mobile app."""
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            username = data.get('username')
            name = data.get('name', '')
            
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Missing user_id'
                }), 400
            
            db.add_user(
                user_id=user_id,
                username=username.lower() if username else None,
                name=name,
                chat_id=None
            )
            
            return jsonify({
                'success': True,
                'message': 'User registered successfully'
            })
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/location-request', methods=['GET'])
    def check_location_request():
        """Check if there's a pending location request for the user."""
        try:
            user_id = request.args.get('user_id')
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
            
            # Check for pending requests from friends
            # For now, return no pending request
            return jsonify({
                'success': True,
                'has_pending_request': False,
                'requester': None
            })
        except Exception as e:
            logger.error(f"Error checking location request: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/get-current-location', methods=['GET'])
    def get_current_location():
        """Get a user's current shared location (if any)."""
        try:
            user_id = request.args.get('user_id')
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
            
            # Return current location if shared
            return jsonify({
                'success': True,
                'location': user.get('current_shared_location'),
                'shared_by': user.get('shared_by')
            })
        except Exception as e:
            logger.error(f"Error getting current location: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/update-location', methods=['POST'])
    def update_user_location():
        """Update a user's current location."""
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            accuracy = data.get('accuracy')
            
            if not all([user_id, latitude is not None, longitude is not None]):
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields'
                }), 400
            
            from datetime import datetime
            db.update_user_location(
                user_id=user_id,
                latitude=float(latitude),
                longitude=float(longitude),
                accuracy=accuracy,
                timestamp=datetime.now()
            )
            
            return jsonify({
                'success': True,
                'message': 'Location updated successfully'
            })
        except Exception as e:
            logger.error(f"Error updating location: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/submit-location', methods=['POST'])
    def submit_location():
        """Submit a new location (building/location) to the database."""
        try:
            data = request.get_json()
            name = data.get('name')
            description = data.get('description', '')
            category = data.get('category', 'building')
            campus_id = data.get('campus_id')
            floor = data.get('floor', 1)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            submitted_by = data.get('submitted_by', 'unknown')
            
            if not all([name, campus_id, latitude, longitude]):
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields'
                }), 400
            
            result = db.add_location(
                name=name,
                description=description,
                category=category,
                campus_id=campus_id,
                floor=int(floor),
                latitude=float(latitude),
                longitude=float(longitude),
                submitted_by=submitted_by
            )
            
            if result:
                return jsonify({
                    'success': True,
                    'message': 'Location submitted successfully',
                    'location_id': str(result) if result else None
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to create share record'
                }), 500
        except Exception as e:
            logger.error(f"Error submitting location: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/instant-share', methods=['POST'])
    def instant_share_location():
        """Instantly share current GPS location to a friend."""
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            friend_username = data.get('friend_username')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if not all([user_id, friend_username, latitude, longitude]):
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields'
                }), 400
            
            friend = db.get_user(username=friend_username.lower())
            if not friend:
                return jsonify({
                    'success': False,
                    'error': 'Friend not found. They need to start the bot first.'
                }), 404
            
            # Store the shared location for the friend
            db.share_location_to_user(
                to_user_id=friend.get('user_id'),
                from_user_id=user_id,
                latitude=float(latitude),
                longitude=float(longitude)
            )
            
            return jsonify({
                'success': True,
                'message': f'Location shared to {friend_username}'
            })
        except Exception as e:
            logger.error(f"Error in instant share: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    logger.info("API routes registered successfully")