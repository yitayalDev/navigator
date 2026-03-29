"""
MongoDB Database Module for UOG Student Navigator
Handles all database operations for users, locations, and sharing.
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import config

logger = logging.getLogger(__name__)


def convert_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    
    # Handle lists
    if isinstance(doc, list):
        return [convert_doc(d) for d in doc]
    
    # Handle dictionaries
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            # Check for MongoDB ObjectId
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = convert_doc(value)
            elif isinstance(value, list):
                result[key] = convert_doc(value)
            else:
                result[key] = value
        return result
    
    return doc


class Database:
    """MongoDB database handler for UOG Navigator."""
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        """Singleton pattern for database connection."""
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def connect(self) -> bool:
        """
        Connect to MongoDB database.
        Returns True if connection successful, False otherwise.
        """
        try:
            # Debug: Print the MongoDB URI being used (masking password)
            mongo_uri = config.MONGODB_URI
            if mongo_uri and '@' in mongo_uri:
                # Mask password in URI
                parts = mongo_uri.split('@')
                credentials = parts[0].split('://')
                if len(credentials) > 1:
                    user_pass = credentials[1].split(':')
                    if len(user_pass) > 1:
                        masked = f"{credentials[0]}://{user_pass[0]}:****@{parts[1]}"
                    else:
                        masked = mongo_uri
                else:
                    masked = mongo_uri
            else:
                masked = mongo_uri
            logger.info(f"Connecting to MongoDB: {masked}")
            
            # Connect to MongoDB
            self._client = MongoClient(
                config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000
            )
            
            # Get database
            self._db = self._client[config.MONGODB_DB_NAME]
            
            # Test connection
            self._client.server_info()
            
            logger.info(f"✓ Connected to MongoDB: {config.MONGODB_DB_NAME}")
            return True
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB connection timeout: {e}")
            return False
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB error: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if database is connected."""
        if self._client is None:
            return False
        try:
            self._client.server_info()
            return True
        except:
            return False
    
    def get_db(self):
        """Get database instance."""
        return self._db
    
    # =========================================================================
    # USER OPERATIONS
    # =========================================================================
    
    def add_user(self, user_id: int, username: str, name: str, chat_id: int = None) -> bool:
        """
        Add or update a user in the database.
        """
        try:
            # Check if user exists
            existing = self._db.users.find_one({'user_id': user_id})
            
            user_data = {
                'user_id': user_id,
                'username': username.lower() if username else None,
                'name': name,
                'chat_id': chat_id,
                'updated_at': datetime.utcnow()
            }
            
            if existing:
                # Update existing user
                self._db.users.update_one(
                    {'user_id': user_id},
                    {'$set': user_data}
                )
            else:
                # Insert new user
                user_data['created_at'] = datetime.utcnow()
                self._db.users.insert_one(user_data)
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int = None, username: str = None) -> Optional[Dict]:
        """Get user by user_id or username."""
        try:
            query = {}
            if user_id:
                query['user_id'] = user_id
            elif username:
                query['username'] = username.lower()
            else:
                return None
            
            return self._db.users.find_one(query)
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all registered users."""
        try:
            # Ensure connected
            if not hasattr(self, '_db') or self._db is None:
                self.connect()
            if self._db is None:
                return []
            return list(self._db.users.find({}))
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def update_user_chat_id(self, user_id: int, chat_id: int) -> bool:
        """Update user's Telegram chat ID."""
        try:
            self._db.users.update_one(
                {'user_id': user_id},
                {'$set': {'chat_id': chat_id, 'updated_at': datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating chat_id: {e}")
            return False
    
    def update_user_location(self, user_id: int, coords: str) -> bool:
        """Update user's current GPS location."""
        try:
            self._db.users.update_one(
                {'user_id': user_id},
                {'$set': {'last_location': coords, 'location_updated_at': datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user location: {e}")
            return False
    
    # =========================================================================
    # LOCATION SHARING OPERATIONS
    # =========================================================================
    
    def create_location_share(self, sender_id: int, sender_name: str, 
                              friend_username: str, coords: str, 
                              location_name: str = "Shared Location") -> Optional[str]:
        """
        Create a new location share record.
        Returns the share_id if successful.
        """
        try:
            share_data = {
                'sender_id': sender_id,
                'sender_name': sender_name,
                'friend_username': friend_username.lower(),
                'coords': coords,
                'location_name': location_name,
                'status': 'pending',  # pending, delivered, read
                'created_at': datetime.utcnow()
            }
            
            result = self._db.shares.insert_one(share_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating share: {e}")
            return None
    
    def get_pending_shares(self, username: str) -> List[Dict]:
        """Get all pending shares for a user."""
        try:
            return list(self._db.shares.find({
                'friend_username': username.lower(),
                'status': 'pending'
            }).sort('created_at', -1))
        except Exception as e:
            logger.error(f"Error getting shares: {e}")
            return []
    
    def mark_share_delivered(self, share_id: str) -> bool:
        """Mark a share as delivered."""
        try:
            self._db.shares.update_one(
                {'_id': self._get_object_id(share_id)},
                {'$set': {'status': 'delivered', 'delivered_at': datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking share delivered: {e}")
            return False
    
    def mark_share_read(self, share_id: str) -> bool:
        """Mark a share as read."""
        try:
            self._db.shares.update_one(
                {'_id': self._get_object_id(share_id)},
                {'$set': {'status': 'read', 'read_at': datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking share read: {e}")
            return False
    
    def get_share_history(self, user_id: int = None, username: str = None, 
                          limit: int = 50) -> List[Dict]:
        """Get location share history."""
        try:
            query = {}
            if user_id:
                query['$or'] = [
                    {'sender_id': user_id},
                    {'friend_username': username.lower() if username else None}
                ]
            
            shares = self._db.shares.find(query).sort('created_at', -1).limit(limit)
            return list(shares)
        except Exception as e:
            logger.error(f"Error getting share history: {e}")
            return []
    
    # =========================================================================
    # CAMPUS LOCATIONS OPERATIONS
    # =========================================================================
    
    def get_campus_locations(self, campus_id: str = None, category: str = None) -> List[Dict]:
        """Get campus locations with optional filters."""
        try:
            query = {}
            if campus_id:
                query['campus'] = campus_id
            if category:
                query['category'] = category
            
            locations = list(self._db.campus_locations.find(query))
            return convert_doc(locations)
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []
    
    def add_campus_location(self, location_data: Dict) -> bool:
        """Add a new campus location."""
        try:
            location_data['created_at'] = datetime.utcnow()
            self._db.campus_locations.insert_one(location_data)
            return True
        except Exception as e:
            logger.error(f"Error adding location: {e}")
            return False
    
    # =========================================================================
    # BUILDING OPERATIONS (Admin CRUD)
    # =========================================================================
    
    def get_all_buildings(self, page: int = 1, per_page: int = 20, 
                          category: str = None, campus: str = None, 
                          search: str = None) -> tuple:
        """Get all buildings with pagination and filters."""
        try:
            query = {}
            
            if category:
                query['category'] = category
            if campus:
                query['campus'] = campus
            if search:
                query['name'] = {'$regex': search, '$options': 'i'}
            
            total = self._db.campus_locations.count_documents(query)
            buildings = list(
                self._db.campus_locations.find(query)
                .sort('created_at', -1)
                .skip((page - 1) * per_page)
                .limit(per_page)
            )
            
            return buildings, total
        except Exception as e:
            logger.error(f"Error getting buildings: {e}")
            return [], 0
    
    def get_building_by_id(self, building_id: str) -> Optional[Dict]:
        """Get a building by its ID."""
        try:
            from bson.objectid import ObjectId
            return self._db.campus_locations.find_one({'_id': ObjectId(building_id)})
        except Exception as e:
            logger.error(f"Error getting building: {e}")
            return None
    
    def add_building(self, name: str, category: str, campus: str, 
                     coords: str, description: str = '', 
                     is_active: bool = True) -> Optional[str]:
        """Add a new building."""
        try:
            # Check if database is connected
            if not self.is_connected():
                logger.error("Database not connected")
                print("DEBUG: Database not connected!")
                return None
            
            print(f"DEBUG DB: Adding building to MongoDB - name: {name}, category: {category}, campus: {campus}")
            
            building_data = {
                'name': name,
                'category': category,
                'campus': campus,
                'coords': coords,
                'description': description,
                'is_active': is_active,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = self._db.campus_locations.insert_one(building_data)
            print(f"DEBUG DB: Insert result: {result.inserted_id}")
            logger.info(f"Building added successfully: {name}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error adding building: {e}")
            print(f"DEBUG DB: Error adding building: {e}")
            return None
    
    def update_building(self, building_id: str, name: str, category: str, 
                        campus: str, coords: str, description: str = '',
                        is_active: bool = True) -> bool:
        """Update an existing building."""
        try:
            from bson.objectid import ObjectId
            
            update_data = {
                'name': name,
                'category': category,
                'campus': campus,
                'coords': coords,
                'description': description,
                'is_active': is_active,
                'updated_at': datetime.utcnow()
            }
            
            result = self._db.campus_locations.update_one(
                {'_id': ObjectId(building_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating building: {e}")
            return False
    
    def delete_building(self, building_id: str) -> bool:
        """Delete a building."""
        try:
            from bson.objectid import ObjectId
            result = self._db.campus_locations.delete_one({'_id': ObjectId(building_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting building: {e}")
            return False
    
    def get_building_count_by_category(self) -> List[Dict]:
        """Get building count grouped by category."""
        try:
            pipeline = [
                {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]
            return list(self._db.campus_locations.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error getting category counts: {e}")
            return []
    
    def get_building_count_by_campus(self) -> List[Dict]:
        """Get building count grouped by campus."""
        try:
            pipeline = [
                {'$group': {'_id': '$campus', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]
            return list(self._db.campus_locations.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error getting campus counts: {e}")
            return []
    
    def get_all_campuses(self) -> List[Dict]:
        """Get all campuses from the campuses collection."""
        try:
            return list(self._db.campuses.find({}))
        except Exception as e:
            logger.error(f"Error getting campuses: {e}")
            return []
    
    def add_campus(self, campus_id: str, name: str, description: str = '', center: str = '') -> bool:
        """Add a new campus."""
        try:
            # Check if campus already exists
            existing = self._db.campuses.find_one({'campus_id': campus_id})
            if existing:
                logger.warning(f"Campus already exists: {campus_id}")
                return False
            
            # Add the new campus
            self._db.campuses.insert_one({
                'campus_id': campus_id,
                'name': name,
                'description': description,
                'center': center,
                'created_at': datetime.utcnow()
            })
            logger.info(f"Added new campus: {campus_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding campus: {e}")
            return False
    
    def delete_campus(self, campus_id: str) -> bool:
        """Delete a campus."""
        try:
            result = self._db.campuses.delete_one({'campus_id': campus_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting campus: {e}")
            return False
    
    def get_recent_buildings(self, limit: int = 10) -> List[Dict]:
        """Get recently added buildings."""
        try:
            return list(
                self._db.campus_locations.find()
                .sort('created_at', -1)
                .limit(limit)
            )
        except Exception as e:
            logger.error(f"Error getting recent buildings: {e}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """Get all unique categories from both custom categories and existing locations."""
        try:
            # Get categories from custom categories collection
            custom_categories = list(self._db.categories.find({}, {'name': 1, '_id': 0}))
            custom_cat_names = [c['name'] for c in custom_categories]
            
            # Get categories from campus_locations
            location_categories = self._db.campus_locations.distinct('category')
            
            # Combine and return unique sorted categories
            all_categories = sorted(set(custom_cat_names + list(location_categories)))
            return all_categories
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    def add_category(self, name: str, description: str = '', icon: str = '📍', color: str = '#3498db') -> bool:
        """Add a new category."""
        try:
            # Check if category already exists
            existing = self._db.categories.find_one({'name': name})
            if existing:
                logger.warning(f"Category already exists: {name}")
                return False
            
            # Add the new category
            self._db.categories.insert_one({
                'name': name,
                'description': description,
                'icon': icon,
                'color': color,
                'created_at': datetime.utcnow()
            })
            logger.info(f"Added new category: {name}")
            return True
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            return False
    
    def delete_category(self, name: str) -> bool:
        """Delete a category."""
        try:
            result = self._db.categories.delete_one({'name': name})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return False
    
    def search_locations(self, query: str) -> List[Dict]:
        """Search locations by name."""
        try:
            return list(self._db.campus_locations.find({
                'name': {'$regex': query, '$options': 'i'}
            }))
        except Exception as e:
            logger.error(f"Error searching locations: {e}")
            return []
    
    def initialize_default_locations(self) -> bool:
        """
        Initialize default campus locations from config.
        This will CLEAR existing data and re-initialize with correct data.
        """
        try:
            # Clear all existing locations first (to remove fake data)
            self._db.campus_locations.delete_many({})
            logger.info("Cleared existing campus locations")
            
            # Import default locations from config
            from utils.config import CampusData
            
            locations_to_insert = []
            for loc in CampusData.LOCATIONS:
                loc_copy = loc.copy()
                loc_copy['created_at'] = datetime.utcnow()
                locations_to_insert.append(loc_copy)
            
            if locations_to_insert:
                self._db.campus_locations.insert_many(locations_to_insert)
                logger.info(f"Added {len(locations_to_insert)} default campus locations")
            
            return True
        except Exception as e:
            logger.error(f"Error initializing locations: {e}")
            return False
    
    # =========================================================================
    # ADMIN USER METHODS
    # =========================================================================
    
    def create_admin_user(self, username: str, password: str) -> bool:
        """Create a new admin user with hashed password."""
        try:
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt()
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            
            user = {
                'username': username,
                'password': hashed_password,
                'created_at': datetime.utcnow()
            }
            
            self._db.admin_users.insert_one(user)
            logger.info(f"Created admin user: {username}")
            return True
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            return False
    
    def get_admin_user(self, username: str) -> Optional[Dict]:
        """Get admin user by username."""
        try:
            return self._db.admin_users.find_one({'username': username})
        except Exception as e:
            logger.error(f"Error getting admin user: {e}")
            return None
    
    def verify_password(self, username: str, password: str) -> bool:
        """Verify admin user password."""
        try:
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt()
            
            user = self.get_admin_user(username)
            if not user:
                return False
            
            return bcrypt.check_password_hash(user['password'], password)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def initialize_default_admin(self, username: str = 'admin123', password: str = '123') -> bool:
        """Initialize default admin user if not exists."""
        try:
            existing_user = self.get_admin_user(username)
            if existing_user:
                logger.info(f"Admin user '{username}' already exists")
                return True
            
            return self.create_admin_user(username, password)
        except Exception as e:
            logger.error(f"Error initializing default admin: {e}")
            return False
    
    def update_admin_password(self, username: str, new_password: str) -> bool:
        """Update admin user password."""
        try:
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt()
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            
            result = self._db.admin_users.update_one(
                {'username': username},
                {'$set': {'password': hashed_password}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating admin password: {e}")
            return False
    
    def create_sms_verification(self, username: str, phone: str, code: str) -> bool:
        """Create or update SMS verification code for admin user."""
        try:
            # Delete any existing codes for this username
            self._db.sms_verifications.delete_many({'username': username})
            
            # Create new verification record
            verification = {
                'username': username,
                'phone': phone,
                'code': code,
                'attempts': 0,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(minutes=10)
            }
            
            self._db.sms_verifications.insert_one(verification)
            logger.info(f"Created SMS verification for {username}")
            return True
        except Exception as e:
            logger.error(f"Error creating SMS verification: {e}")
            return False
    
    def verify_sms_code(self, username: str, code: str) -> bool:
        """Verify SMS code for admin user."""
        try:
            verification = self._db.sms_verifications.find_one({
                'username': username,
                'code': code
            })
            
            if not verification:
                return False
            
            # Check if expired
            if datetime.utcnow() > verification['expires_at']:
                self._db.sms_verifications.delete_one({'username': username})
                return False
            
            # Check attempts
            if verification['attempts'] >= 3:
                self._db.sms_verifications.delete_one({'username': username})
                return False
            
            # Delete the code after successful verification
            self._db.sms_verifications.delete_one({'username': username})
            return True
        except Exception as e:
            logger.error(f"Error verifying SMS code: {e}")
            return False
    
    def increment_sms_attempts(self, username: str) -> int:
        """Increment failed attempt counter for SMS verification."""
        try:
            result = self._db.sms_verifications.update_one(
                {'username': username},
                {'$inc': {'attempts': 1}}
            )
            verification = self._db.sms_verifications.find_one({'username': username})
            return verification['attempts'] if verification else 0
        except Exception as e:
            logger.error(f"Error incrementing SMS attempts: {e}")
            return 0
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_object_id(self, id_str: str):
        """Convert string to MongoDB ObjectId."""
        from bson.objectid import ObjectId
        try:
            return ObjectId(id_str)
        except:
            return None
    
    def close(self):
        """Close database connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")


# Create global database instance
db = Database()