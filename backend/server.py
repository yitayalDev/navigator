"""
UOG Student Navigation Flask Server
Handles API requests from the mobile app and Telegram bot webhooks
"""
import os
import sys
import asyncio
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, make_response, flash, session
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from dotenv import load_dotenv
from pathlib import Path
import logging

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Import from config and other modules
from config import config, CampusData
from routing_service import routing_service
from database import db

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = 'uog-navigator-admin-secret-key'

# Initialize Flask-Bcrypt
bcrypt = Bcrypt(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username
    
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    # Try to find user by the ID
    from bson import ObjectId
    try:
        user = db._db.admin_users.find_one({'_id': ObjectId(user_id)})
        if user:
            return User(str(user['_id']), user['username'])
    except:
        # If ID is username, try that way
        user = db.get_admin_user(user_id)
        if user:
            return User(str(user['_id']), user['username'])
    return None

# Redirect root to admin
@app.route('/')
def index():
    return redirect('/admin')

# Serve Flutter web app from /app route
@app.route('/app')
def serve_flutter_app():
    """Serve the Flutter web app"""
    flutter_build_path = Path(__file__).parent.parent / 'frontend' / 'build' / 'web'
    
    # Read index.html from Flutter build
    index_path = flutter_build_path / 'index.html'
    if index_path.exists():
        with open(index_path, 'r') as f:
            content = f.read()
        # Update base href for Flask routing
        content = content.replace('<base href="/">', '<base href="/app/">')
        return content
    else:
        return "Flutter app not found. Please run 'flutter build web' first.", 404

@app.route('/app/<path:filename>')
def serve_flutter_static(filename):
    """Serve static files from Flutter build"""
    flutter_build_path = Path(__file__).parent.parent / 'frontend' / 'build' / 'web'
    file_path = flutter_build_path / filename
    
    if file_path.exists():
        # Determine content type
        import mimetypes
        content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
        
        with open(file_path, 'rb') as f:
            return f.read(), 200, {'Content-Type': content_type}
    else:
        return "File not found", 404

# Enable CORS for all routes (needed for Flutter web)
CORS(app)

# Custom JSON encoder to handle ObjectId
class MongoJSONProvider(app.json_provider_class):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

app.json_provider = MongoJSONProvider(app)
app.json = app.json_provider


def register_user(update: Update):
    """Register a user who started the bot in MongoDB."""
    user = update.effective_user
    if user:
        username = user.username.lower() if user.username else None
        db.add_user(
            user_id=user.id,
            username=username,
            name=user.first_name,
            chat_id=update.effective_chat.id
        )


def get_user_chat_id(identifier):
    """Get chat_id for a user by username or user_id from MongoDB."""
    identifier = str(identifier).lower() if not isinstance(identifier, int) else identifier
    
    if isinstance(identifier, str):
        user = db.get_user(username=identifier)
    else:
        user = db.get_user(user_id=identifier)
    
    if user:
        return user.get('chat_id')
    return None


def get_category_emoji(category: str) -> str:
    """Get emoji for category."""
    emojis = {
        'building': '🏢',
        'cafe': '☕',
        'library': '📚',
        'lecture_hall': '🎓',
        'lab': '🔬',
        'laboratory': '🔬'
    }
    return emojis.get(category, '📍')


def get_category_display_name(category: str) -> str:
    """Get display name for category."""
    names = {
        'building': 'Buildings',
        'cafe': 'Cafés & Food',
        'library': 'Libraries',
        'lecture_hall': 'Lecture Halls',
        'lab': 'Labs',
        'laboratory': 'Laboratories'
    }
    return names.get(category, category.title())


# Default categories for the admin panel
DEFAULT_CATEGORIES = ['building', 'administration', 'library', 'lab', 'cafe', 'dorm', 'lecture_hall']

# ============================================================================
# FLASK ROUTES - ADMIN PANEL
# ============================================================================

def get_categories_list():
    """Get categories list with fallback to default categories."""
    try:
        if db.is_connected():
            categories = db.get_all_categories()
            if categories:
                return categories
        return DEFAULT_CATEGORIES
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return DEFAULT_CATEGORIES


def get_campuses_for_template():
    """Get campuses from both MongoDB and hardcoded for template rendering."""
    try:
        # Get campuses from database
        db_campuses = db.get_all_campuses()
        
        # Build campuses dict from MongoDB
        campuses_dict = {}
        for campus in db_campuses:
            campus_id = campus.get('campus_id', '')
            campuses_dict[campus_id] = {
                'name': campus.get('name', ''),
                'description': campus.get('description', ''),
                'center': campus.get('center', '')
            }
        
        # Also include hardcoded campuses that aren't in database
        for campus_id, campus_info in CampusData.CAMPUSES.items():
            if campus_id not in campuses_dict:
                campuses_dict[campus_id] = {
                    'name': campus_info['name'],
                    'description': campus_info.get('description', ''),
                    'center': campus_info.get('center', '')
                }
        
        return campuses_dict
    except Exception as e:
        logger.error(f"Error getting campuses for template: {e}")
        return CampusData.CAMPUSES


# =========================================================================
# LOGIN ROUTES
# =========================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    if current_user.is_authenticated:
        return redirect('/admin')
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Verify credentials
        if db.verify_password(username, password):
            user = db.get_admin_user(username)
            if user:
                user_obj = User(str(user['_id']), user['username'])
                login_user(user_obj)
                next_page = request.args.get('next')
                return redirect(next_page or '/admin')
        
        flash('Invalid username or password', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def logout():
    """Admin logout."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect('/admin/login')


@app.route('/admin', methods=['GET'])
@login_required
def admin_dashboard():
    """Admin dashboard showing statistics."""
    # Get stats
    total_buildings = len(db.get_campus_locations())
    total_categories = len(get_categories_list())
    total_campuses = len(get_campuses_for_template())
    total_users = len(db.get_all_users())
    
    # Get category counts
    category_counts = db.get_building_count_by_category()
    category_colors = {
        'building': 'primary',
        'administration': 'secondary',
        'library': 'info',
        'cafe': 'warning',
        'lab': 'success',
        'laboratory': 'success',
        'lecture_hall': 'danger',
        'dorm': 'dark'
    }
    categories = []
    for cat in category_counts:
        categories.append({
            'id': cat['_id'],
            'name': cat['_id'].replace('_', ' ').title() if cat['_id'] else 'Unknown',
            'count': cat['count'],
            'color': category_colors.get(cat['_id'], 'primary')
        })
    
    # Get campus counts - use MongoDB + hardcoded
    all_campuses = get_campuses_for_template()
    campus_counts = db.get_building_count_by_campus()
    campuses = []
    for camp in campus_counts:
        campus_info = all_campuses.get(camp['_id'], {'name': camp['_id']})
        campuses.append({
            'id': camp['_id'],
            'name': campus_info.get('name', camp['_id']),
            'count': camp['count']
        })
    
    # Get recent buildings
    recent_buildings = db.get_recent_buildings(limit=5)
    
    return render_template('admin/index.html',
        active_page='dashboard',
        stats={
            'total_buildings': total_buildings,
            'total_categories': total_categories,
            'total_campuses': total_campuses,
            'total_users': total_users
        },
        categories=categories,
        campuses=campuses,
        recent_buildings=recent_buildings
    )


@app.route('/admin/buildings', methods=['GET'])
@login_required
def admin_buildings():
    """Manage buildings page."""
    # Get query parameters
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    campus = request.args.get('campus', '')
    
    per_page = 20
    
    # Get buildings with filters
    buildings, total = db.get_all_buildings(
        page=page,
        per_page=per_page,
        category=category if category else None,
        campus=campus if campus else None,
        search=search if search else None
    )
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('admin/buildings.html',
        active_page='buildings',
        buildings=buildings,
        categories_list=get_categories_list(),
        campuses=get_campuses_for_template(),
        page=page,
        total_pages=total_pages,
        total=total
    )


@app.route('/admin/buildings/add', methods=['GET', 'POST'])
@login_required
def admin_add_building():
    """Add new building page."""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            category = request.form.get('category')
            campus = request.form.get('campus')
            coords = request.form.get('coords')
            description = request.form.get('description', '')
            is_active = 'is_active' in request.form
            
            print(f"DEBUG: Adding building - name: {name}, category: {category}, campus: {campus}, coords: {coords}")
            
            # Validate
            if not name or not category or not campus or not coords:
                return render_template('admin/building_form.html',
                    active_page='buildings',
                    building=None,
                    categories_list=get_categories_list(),
                    campuses=get_campuses_for_template(),
                    error='All fields are required'
                )
            
            # Add building
            result = db.add_building(
                name=name,
                category=category,
                campus=campus,
                coords=coords,
                description=description,
                is_active=is_active
            )
            
            print(f"DEBUG: Add building result: {result}")
            
            if result:
                return redirect('/admin/buildings')
            else:
                return render_template('admin/building_form.html',
                    active_page='buildings',
                    building=request.form,
                    categories_list=get_categories_list(),
                    campuses=get_campuses_for_template(),
                    error='Failed to add building - check server logs'
                )
        except Exception as e:
            print(f"DEBUG: Exception adding building: {e}")
            logger.error(f"Error adding building: {e}")
            return render_template('admin/building_form.html',
                active_page='buildings',
                building=request.form,
                categories_list=get_categories_list(),
                campuses=get_campuses_for_template(),
                error=f'Error: {str(e)}'
            )
    
    return render_template('admin/building_form.html',
        active_page='buildings',
        building=None,
        categories_list=get_categories_list(),
        campuses=get_campuses_for_template()
    )


@app.route('/admin/buildings/edit/<building_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_building(building_id):
    """Edit building page."""
    building = db.get_building_by_id(building_id)
    
    if not building:
        return redirect('/admin/buildings')
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            category = request.form.get('category')
            campus = request.form.get('campus')
            coords = request.form.get('coords')
            description = request.form.get('description', '')
            is_active = 'is_active' in request.form
            
            # Update building
            result = db.update_building(
                building_id=building_id,
                name=name,
                category=category,
                campus=campus,
                coords=coords,
                description=description,
                is_active=is_active
            )
            
            if result:
                return redirect('/admin/buildings')
            else:
                return render_template('admin/building_form.html',
                    active_page='buildings',
                    building=request.form,
                    categories_list=get_categories_list(),
                    campuses=get_campuses_for_template(),
                    error='Failed to update building'
                )
        except Exception as e:
            logger.error(f"Error updating building: {e}")
            return render_template('admin/building_form.html',
                active_page='buildings',
                building=request.form,
                categories_list=get_categories_list(),
                campuses=get_campuses_for_template(),
                error=f'Error: {str(e)}'
            )
    
    return render_template('admin/building_form.html',
        active_page='buildings',
        building=building,
        categories_list=get_categories_list(),
        campuses=get_campuses_for_template()
    )


@app.route('/admin/api/buildings/<building_id>', methods=['DELETE'])
@login_required
def admin_delete_building(building_id):
    """API endpoint to delete a building."""
    result = db.delete_building(building_id)
    return jsonify({
        'success': result,
        'message': 'Building deleted successfully' if result else 'Failed to delete building'
    })


@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    """Categories management page."""
    try:
        # Get building counts by category (only categories with buildings)
        category_counts = db.get_building_count_by_category()
        cat_dict = {c['_id']: c['count'] for c in category_counts}
        
        # Get ALL categories from the custom categories collection (including those with 0 buildings)
        custom_cats = list(db._db.categories.find({}, {'name': 1, 'description': 1, 'icon': 1, 'color': 1}))
        
        # Build a list of all categories with their info
        categories = []
        for cat in custom_cats:
            cat_name = cat.get('name', '')
            categories.append({
                'name': cat_name,
                'description': cat.get('description', ''),
                'icon': cat.get('icon', '📍'),
                'color': cat.get('color', '#3498db'),
                'count': cat_dict.get(cat_name, 0)
            })
        
        # Also add categories from campus_locations that aren't in custom categories
        location_cats = db._db.campus_locations.distinct('category')
        existing_names = {c['name'] for c in categories}
        for loc_cat in location_cats:
            if loc_cat not in existing_names:
                categories.append({
                    'name': loc_cat,
                    'description': '',
                    'icon': '📍',
                    'color': '#3498db',
                    'count': cat_dict.get(loc_cat, 0)
                })
        
        # Sort by name
        categories = sorted(categories, key=lambda x: x['name'])
        
    except Exception as e:
        logger.error(f"Error loading categories: {e}")
        categories = []
        cat_dict = {}
    
    # Handle adding new category
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip().lower()
            description = request.form.get('description', '')
            icon = request.form.get('icon', '📍')
            color = request.form.get('color', '#3498db')
            
            if name:
                success = db.add_category(name, description, icon, color)
                if success:
                    flash(f'Category "{name}" added successfully!', 'success')
                else:
                    flash(f'Category "{name}" already exists!', 'warning')
            else:
                flash('Please provide a category name!', 'danger')
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            flash(f'Error adding category: {str(e)}', 'danger')
        
        return redirect('/admin/categories')

    return render_template('admin/categories.html',
        active_page='categories',
        categories=categories,
        category_counts=cat_dict
    )

@app.route('/admin/categories/delete/<category_name>', methods=['POST'])
@login_required
def delete_category(category_name):
    """Delete a category."""
    success = db.delete_category(category_name)
    if success:
        flash(f'Category "{category_name}" deleted successfully!', 'success')
    else:
        flash(f'Failed to delete category "{category_name}"!', 'danger')
    return redirect('/admin/categories')


@app.route('/admin/campuses', methods=['GET', 'POST'])
@login_required
def admin_campuses():
    """Campuses management page."""
    # Handle adding new campus
    if request.method == 'POST':
        try:
            campus_id = request.form.get('campus_id', '').strip().lower()
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '')
            center = request.form.get('center', '')
            
            if campus_id and name:
                success = db.add_campus(campus_id, name, description, center)
                if success:
                    flash(f'Campus "{name}" added successfully!', 'success')
                else:
                    flash(f'Campus ID "{campus_id}" already exists!', 'warning')
            else:
                flash('Please provide campus ID and name!', 'danger')
        except Exception as e:
            logger.error(f"Error adding campus: {e}")
            flash(f'Error adding campus: {str(e)}', 'danger')
        
        return redirect('/admin/campuses')
    
    # Get campuses from database
    db_campuses = db.get_all_campuses()
    campus_counts = db.get_building_count_by_campus()
    
    # Also include hardcoded campuses from CampusData
    camp_data = []
    
    # First add database campuses
    for campus in db_campuses:
        campus_id = campus.get('campus_id', '')
        count = next((c['count'] for c in campus_counts if c['_id'] == campus_id), 0)
        camp_data.append({
            'id': campus_id,
            'name': campus.get('name', ''),
            'description': campus.get('description', ''),
            'center': campus.get('center', ''),
            'count': count,
            'from_db': True
        })
    
    # Then add hardcoded campuses that aren't in database
    for campus_id, campus_info in CampusData.CAMPUSES.items():
        if not any(c['id'] == campus_id for c in camp_data):
            count = next((c['count'] for c in campus_counts if c['_id'] == campus_id), 0)
            camp_data.append({
                'id': campus_id,
                'name': campus_info['name'],
                'description': campus_info.get('description', ''),
                'center': campus_info.get('center', ''),
                'count': count,
                'from_db': False
            })
    
    return render_template('admin/campuses.html',
        active_page='campuses',
        campuses=camp_data
    )


@app.route('/admin/campuses/delete/<campus_id>', methods=['POST'])
@login_required
def delete_campus(campus_id):
    """Delete a campus."""
    success = db.delete_campus(campus_id)
    if success:
        flash(f'Campus "{campus_id}" deleted successfully!', 'success')
    else:
        flash(f'Failed to delete campus "{campus_id}"!', 'danger')
    return redirect('/admin/campuses')


# ============================================================================
# FLASK ROUTES - API FOR MOBILE APP
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Check MongoDB connection
    mongo_status = "connected" if db.is_connected() else "disconnected"
    
    return jsonify({
        'status': 'ok', 
        'service': 'UOG Navigator API',
        'database': {
            'mongodb': mongo_status,
            'db_name': config.MONGODB_DB_NAME
        }
    })


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
            # Check type name for MongoDB ObjectId
            if type(value).__name__ == 'ObjectId':
                result[key] = str(value)
            elif hasattr(value, '__dict__') and isinstance(value, dict):
                result[key] = convert_doc(value)
            elif isinstance(value, list):
                result[key] = convert_doc(value)
            else:
                result[key] = value
        return result
    
    # Handle other objects that might not be JSON serializable
    if hasattr(doc, '__class__'):
        type_name = type(doc).__name__
        if type_name == 'ObjectId':
            return str(doc)
    
    return doc


@app.route('/api/locations', methods=['GET'])
def get_all_locations():
    """Get all campus locations from MongoDB"""
    try:
        # Get locations from MongoDB
        locations = db.get_campus_locations()
        
        # If no locations in DB, initialize with default data
        if not locations:
            db.initialize_default_locations()
            locations = db.get_campus_locations()
        
        # Get campuses from MongoDB
        db_campuses = db.get_all_campuses()
        campus_counts = db.get_building_count_by_campus()
        
        # Build campuses list from MongoDB
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
        
        # Also include hardcoded campuses that aren't in database
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
        logger.error(f"Error getting locations: {e}")
        response = make_response(json.dumps({'success': False, 'error': str(e)}))
        response.headers['Content-Type'] = 'application/json'
        return response, 500


@app.route('/api/locations/<campus_id>', methods=['GET'])
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


@app.route('/api/locations/category/<category>', methods=['GET'])
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


@app.route('/api/categories', methods=['GET'])
def get_all_categories_api():
    """Get all categories from both custom categories and campus_locations"""
    try:
        # Get custom categories
        custom_cats = list(db._db.categories.find({}, {'name': 1, 'description': 1, 'icon': 1, 'color': 1}))
        custom_cat_names = [c['name'] for c in custom_cats]
        
        # Get categories from campus_locations
        location_categories = db._db.campus_locations.distinct('category')
        
        # Combine and get unique categories
        all_categories = sorted(set(custom_cat_names + list(location_categories)))
        
        # Get counts for each category
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
        logger.error(f"Error getting categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/campuses', methods=['GET'])
def get_all_campuses_api():
    """Get all campuses from MongoDB"""
    try:
        # Get campuses from database
        db_campuses = db.get_all_campuses()
        campus_counts = db.get_building_count_by_campus()
        
        # Also include hardcoded campuses from CampusData
        all_campuses = []
        
        # First add database campuses
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
        
        # Then add hardcoded campuses that aren't in database
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
        logger.error(f"Error getting campuses: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/share-location', methods=['POST'])
def share_location_to_friend():
    """
    API endpoint for the mobile app to share location to a friend
    Request body: {
        "sender_id": "telegram_user_id",
        "friend_username": "friend_username", 
        "coords": "lat,lng",
        "location_name": "Location Name"
    }
    """
    data = request.json
    
    sender_id = data.get('sender_id')
    friend_username = data.get('friend_username', '').strip().lower()
    coords = data.get('coords')
    location_name = data.get('location_name', 'Shared Location')
    sender_name = data.get('sender_name', 'A friend')
    
    # Check for pending share request
    sender_id_int = int(sender_id) if sender_id else 0
    pending = None
    if sender_id_int in pending_shares:
        pending = pending_shares[sender_id_int]
        if pending.get('state') == 'waiting_location':
            friend_username = pending.get('friend_username', friend_username)
            sender_name = pending.get('sender_name', sender_name)
    
    if not friend_username or not coords:
        return jsonify({
            'success': False, 
            'error': 'Missing friend_username or coords'
        }), 400
    
    # Get friend's chat_id
    friend_chat_id = get_user_chat_id(friend_username)
    
    if not friend_chat_id:
        return jsonify({
            'success': False,
            'error': f'User @{friend_username} has not started the bot yet'
        }), 404
    
    # Create share record in MongoDB
    share_id = db.create_location_share(
        sender_id=sender_id_int,
        sender_name=sender_name,
        friend_username=friend_username,
        coords=coords,
        location_name=location_name
    )
    
    if not share_id:
        return jsonify({
            'success': False,
            'error': 'Failed to create share record'
        }), 500
    
    # Create share message
    maps_url = f"https://www.google.com/maps?q={coords}"
    
    share_message = f"""
📍 *Location Shared by Friend*

👤 *From:* {sender_name}

📍 *Location:* {location_name}
📌 *Coordinates:* {coords}

🗺️ [View on Google Maps]({maps_url})

_Sent via UOG Navigator Bot_
"""
    
    # Send message to friend's Telegram
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(application.bot.send_message(
            chat_id=friend_chat_id,
            text=share_message,
            parse_mode='Markdown'
        ))
    except Exception as e:
        logger.error(f"Error sending location to Telegram: {e}")
    
    # Clean up pending share
    if sender_id_int in pending_shares:
        del pending_shares[sender_id_int]
    
    return jsonify({
        'success': True,
        'message': f'Location sent to @{friend_username}',
        'share_id': share_id,
        'share_details': {
            'to': friend_username,
            'coords': coords,
            'location_name': location_name,
            'maps_url': maps_url
        }
    })


@app.route('/api/register-user', methods=['POST'])
def register_app_user():
    """
    Register a user from the mobile app
    Request body: {
        "user_id": "telegram_user_id",
        "username": "telegram_username",
        "name": "User Name"
    }
    """
    data = request.json
    
    user_id = str(data.get('user_id', ''))
    username = data.get('username', '').strip().lower()
    name = data.get('name', 'Unknown')
    
    if user_id:
        # Store user in MongoDB
        db.add_user(
            user_id=int(user_id) if user_id.isdigit() else 0,
            username=username,
            name=name,
            chat_id=None  # App users don't have Telegram chat_id
        )
    
    return jsonify({
        'success': True,
        'message': 'User registered successfully'
    })


# ============================================================================
# TELEGRAM BOT HANDLERS
# ============================================================================

# Conversation states for share location
(ASK_FRIEND_USERNAME, CONFIRM_SEND) = range(2)

# Store pending share requests
pending_shares = {}  # user_id -> {'friend_username': ..., 'timestamp': ...}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    register_user(update)
    
    keyboard = [
        [
            InlineKeyboardButton("🏫 Maraki Campus", callback_data='campus_maraki'),
        ],
        [
            InlineKeyboardButton("🏢 Tewodros Campus", callback_data='campus_tewodros'),
        ],
        [
            InlineKeyboardButton("🏥 Fasil Campus", callback_data='campus_fasil'),
        ],
        [
            InlineKeyboardButton("📤 Share My Location", callback_data='share_location_start'),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
🏛️ *Welcome to UOG Student Navigation Bot!*

I can help you navigate the University of Gondar campuses.

*Please select a campus to explore:*
"""
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_message = """
📚 *Available Commands:*

/start - Start the bot
/menu - Show main menu
/campuses - List all campuses
/locations - Show all locations
/buildings - Show only buildings
/cafes - Show only cafes
/libraries - Show only libraries

📤 *Share Location:*
Use /menu and click "Share My Location" button!

🔹 *Campus Codes:*
• maraki - Main Campus
• tewodros - Tewodros Campus  
• fasil - Fasil Campus
"""
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def locations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all locations"""
    message = "📍 *All University Locations:*\n\n"
    
    # Get locations from MongoDB
    locations = db.get_campus_locations()
    if not locations:
        locations = CampusData.LOCATIONS  # Fallback to static
    
    for loc in locations:
        emoji = get_category_emoji(loc['category'])
        message += f"{emoji} *{loc['name']}*\n"
        message += f"   📌 {loc['campus'].title()} Campus\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu with Share Location button"""
    register_user(update)
    
    keyboard = [
        [
            InlineKeyboardButton("🏫 Maraki Campus", callback_data='campus_maraki'),
        ],
        [
            InlineKeyboardButton("🏢 Tewodros Campus", callback_data='campus_tewodros'),
        ],
        [
            InlineKeyboardButton("🏥 Fasil Campus", callback_data='campus_fasil'),
        ],
        [
            InlineKeyboardButton("📤 Share My Location", callback_data='share_location_start'),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏛️ *UOG Student Navigation*\n\nSelect an option:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith('campus_'):
        campus_id = callback_data.replace('campus_', '')
        # Get locations from MongoDB
        locations = db.get_campus_locations(campus_id=campus_id)
        if not locations:
            locations = CampusData.get_locations_by_campus(campus_id)  # Fallback
        campus_info = CampusData.CAMPUSES.get(campus_id, {})
        
        if locations:
            categories = {}
            for loc in locations:
                category = loc['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append(loc)
            
            keyboard = []
            for category, locs in categories.items():
                emoji = get_category_emoji(category)
                category_display = get_category_display_name(category)
                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {category_display} ({len(locs)})", 
                        callback_data=f'category_{campus_id}_{category}'
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Campuses", callback_data='back_campuses')
            ])
            
            message = f"🏛️ *{campus_info.get('name', campus_id.title())} Campus*\n\n"
            message += f"📊 Total locations: {len(locations)}\n\n"
            message += "*Select a category:*"
            
            await query.edit_message_text(
                text=message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif callback_data.startswith('category_'):
        parts = callback_data.split('_')
        if len(parts) >= 3:
            campus_id = parts[1]
            category = parts[2]
            
            # Get locations from MongoDB
            locations = db.get_campus_locations(campus_id=campus_id)
            if not locations:
                locations = CampusData.get_locations_by_campus(campus_id)  # Fallback
            locations = [loc for loc in locations if loc.get('category') == category]
            campus_info = CampusData.CAMPUSES.get(campus_id, {})
            category_display = get_category_display_name(category)
            emoji = get_category_emoji(category)
            
            if locations:
                keyboard = []
                for loc in locations:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📍 {loc['name']}", 
                            callback_data=f'location_{loc["name"]}'
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(f"🔙 Back", callback_data=f'campus_{campus_id}')
                ])
                
                message = f"{emoji} *{category_display} in {campus_info.get('name', campus_id.title())} Campus*\n\n"
                message += f"📊 {len(locations)} location(s)\n\n"
                message += "Select a location:"
                
                await query.edit_message_text(
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
    
    elif callback_data.startswith('location_'):
        location_name = callback_data.replace('location_', '')
        
        # Get all locations from MongoDB
        locations = db.get_campus_locations()
        if not locations:
            locations = CampusData.LOCATIONS  # Fallback
        
        for loc in locations:
            if location_name.lower() == loc['name'].lower():
                maps_url = f"https://www.google.com/maps/search/?api=1&query={loc['coords']}"
                
                message = f"""
📍 *{loc['name']}*

🏛️ Campus: {loc['campus'].title()}
📝 {loc['description']}
📌 Coordinates: {loc['coords']}

[📍 View on Google Maps]({maps_url})
"""
                
                await query.edit_message_text(
                    text=message,
                    parse_mode='Markdown'
                )
                break
    
    elif callback_data == 'back_campuses':
        keyboard = [
            [InlineKeyboardButton("🏫 Maraki Campus", callback_data='campus_maraki')],
            [InlineKeyboardButton("🏢 Tewodros Campus", callback_data='campus_tewodros')],
            [InlineKeyboardButton("🏥 Fasil Campus", callback_data='campus_fasil')],
            [InlineKeyboardButton("📤 Share My Location", callback_data='share_location_start')],
        ]
        
        await query.edit_message_text(
            text="🏛️ *Select a Campus:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif callback_data == 'share_location_start':
        """Start share location flow"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Ask for friend's username
        await query.edit_message_text(
            text="📤 Share Your Location\n\n"
                "Please enter the Telegram username of your friend\n"
                "who you want to share your location with.\n\n"
                "Example: friend_username\n\n"
                "Note: Your friend must have started the bot at least once.",
            parse_mode=None
        )
        
        # Store that user is in share location flow
        pending_shares[user_id] = {'state': 'waiting_username', 'timestamp': datetime.now()}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Check if user is in share location flow
    if user_id in pending_shares:
        share_data = pending_shares[user_id]
        
        if share_data.get('state') == 'waiting_username':
            # Get friend's username
            friend_username = text.strip()
            if friend_username.startswith('@'):
                friend_username = friend_username[1:]
            friend_username = friend_username.lower()
            
            # Check if friend exists in database
            friend = db.get_user(username=friend_username)
            
            if not friend:
                await update.message.reply_text(
                    f"❌ User @{friend_username} not found!\n\n"
                    f"Please make sure your friend has started the bot first.",
                    parse_mode='Markdown'
                )
                del pending_shares[user_id]
                return
            
            # Store friend's username and ask user to open app
            pending_shares[user_id] = {
                'state': 'waiting_location',
                'friend_username': friend_username,
                'sender_name': username,
                'timestamp': datetime.now()
            }
            
            await update.message.reply_text(
                f"✅ Friend found: @{friend_username}\n\n"
                f"📱 *Now please open the UOG Navigator app and share your location.*\n\n"
                f"The app will automatically send your location to @{friend_username}.\n\n"
                f"⏳ Waiting for location...\n\n"
                f"Or click /cancel to cancel.",
                parse_mode='Markdown'
            )
            return
        
        elif share_data.get('state') == 'waiting_location':
            await update.message.reply_text(
                "⏳ Please wait for the location from the app, or click /cancel to cancel."
            )
            return
    
    if text == '/start':
        await start_command(update, context)
    elif text == '/help':
        await help_command(update, context)
    elif text == '/locations':
        await locations_command(update, context)
    elif text == '/menu':
        await menu_command(update, context)
    elif text == '/cancel':
        if user_id in pending_shares:
            del pending_shares[user_id]
        await update.message.reply_text("❌ Share location cancelled.")
    else:
        # Search for location in MongoDB
        text_lower = text.lower()
        locations = db.get_campus_locations()
        if not locations:
            locations = CampusData.LOCATIONS  # Fallback
        
        for loc in locations:
            if text_lower in loc['name'].lower():
                maps_url = f"https://www.google.com/maps/search/?api=1&query={loc['coords']}"
                await update.message.reply_text(
                    f"📍 *{loc['name']}*\n\n"
                    f"Campus: {loc['campus'].title()}\n"
                    f"Coordinates: {loc['coords']}\n\n"
                    f"[View on Maps]({maps_url})",
                    parse_mode='Markdown'
                )
                return
        
        await update.message.reply_text(
            "❓ Use /locations to see all places or /help for commands."
        )


# ============================================================================
# TELEGRAM WEBHOOK
# ============================================================================

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook updates"""
    update = Update.de_json(request.get_json(force=True), application.bot)
    
    # Process the update asynchronously
    asyncio.create_task(application.process_update(update))
    
    return 'ok'


# ============================================================================
# MAIN
# ============================================================================

# Global application object
application = None


def main():
    """Main function to run the server"""
    global application
    
    # Validate config
    if not config.validate():
        print("\n" + "="*50)
        print("ERROR: Bot configuration is incomplete!")
        print("="*50)
        sys.exit(1)
    
    # Connect to MongoDB
    print("\n" + "="*50)
    print("Connecting to MongoDB...")
    print("="*50)
    
    if not db.connect():
        print("\n" + "="*50)
        print("WARNING: Could not connect to MongoDB!")
        print("The server will run but location sharing may not work.")
        print("Make sure MongoDB is running and configured in .env")
        print("="*50 + "\n")
    else:
        # Only initialize default locations if database is empty
        existing_locations = db.get_campus_locations()
        if not existing_locations:
            print("No locations found in database. Initializing default locations...")
            db.initialize_default_locations()
        else:
            print(f"Found {len(existing_locations)} locations in database. Keeping existing data.")
        
        # Initialize default admin user
        print("Initializing default admin user...")
        if db.initialize_default_admin('admin123', '123'):
            print("Default admin user created: admin123")
        else:
            print("Admin user already exists or error occurred.")
    
    # Build Telegram application
    bot_token = config.get_bot_token()
    application = ApplicationBuilder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('menu', menu_command))
    application.add_handler(CommandHandler('locations', locations_command))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("\n" + "="*50)
    print("UOG Student Navigation Server")
    print("="*50)
    print("Bot handlers registered")
    print(f"API available at: http://localhost:5000")
    print("="*50 + "\n")
    
    # Run Flask app (with bot polling OR webhook)
    # For webhook mode, you need to set WEBHOOK_URL environment variable
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if webhook_url:
        # Webhook mode
        application.run_webhook(
            listen='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            url_path='webhook',
            webhook_url=webhook_url
        )
    else:
        # Polling mode (for local development)
        # Start Flask in background thread
        import threading
        flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False))
        flask_thread.daemon = True
        flask_thread.start()
        
        # Run bot with polling
        application.run_polling()


if __name__ == '__main__':
    import asyncio
    main()
