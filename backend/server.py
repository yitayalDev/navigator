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
        'building': 'ðŸ¢',
        'cafe': 'â˜•',
        'library': 'ðŸ“š',
        'lecture_hall': 'ðŸŽ“',
        'lab': 'ðŸ”¬',
        'laboratory': 'ðŸ”¬'
    }
    return emojis.get(category, 'ðŸ“')


def get_category_display_name(category: str) -> str:
    """Get display name for category."""
    names = {
        'building': 'Buildings',
        'cafe': 'CafÃ©s & Food',
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
                'icon': cat.get('icon', 'ðŸ“'),
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
                    'icon': 'ðŸ“',
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
            icon = request.form.get('icon', 'ðŸ“')
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


@app.route('/api/users', methods=['GET'])
def get_all_users_api():
    """
    Get all registered users (Telegram bot users) for location sharing.
    Returns list of users with their usernames who have started the bot.
    """
    try:
        # Ensure database is connected
        db.connect()
        users = db.get_all_users()
        # Return only username and name (not chat_id or sensitive info)
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
        logger.error(f"Error getting users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/share-location', methods=['POST'])
def share_location_to_friend():
    """
    API endpoint for the mobile app to share location to a friend INSTANTLY
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
    
    # INSTANT SHARE: No need to check for pending shares - directly send to friend
    sender_id_int = int(sender_id) if sender_id else 0
    
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
ðŸ“ *Location Shared by Friend*

ðŸ‘¤ *From:* {sender_name}

ðŸ“ *Location:* {location_name}
ðŸ“Œ *Coordinates:* {coords}

ðŸ—ºï¸ [View on Google Maps]({maps_url})

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


@app.route('/api/location-request', methods=['GET'])
def check_location_request():
    """
    App polls this endpoint to check if bot requested location
    Query params: user_id (the Telegram user ID)
    Returns: {"requested": true, "timestamp": ...} or {"requested": false}
    """
    user_id = request.args.get('user_id', '')
    
    if not user_id:
        return jsonify({'requested': False})
    
    user_id_int = int(user_id) if user_id.isdigit() else 0
    
    # Check if there's a pending location request
    if user_id_int in pending_shares:
        share_data = pending_shares[user_id_int]
        if share_data.get('state') == 'waiting_location_from_app':
            return jsonify({
                'requested': True,
                'timestamp': share_data.get('timestamp', '').isoformat() if share_data.get('timestamp') else '',
                'friend_username': share_data.get('friend_username', '')
            })
    
    return jsonify({'requested': False})


@app.route('/api/get-current-location', methods=['GET'])
def get_current_location():
    """
    Get current location from a user (called by bot when sharing location)
    Query params: user_id (the Telegram user ID)
    Returns: {"coords": "lat,lng"} or {"error": "No location"}
    """
    user_id = request.args.get('user_id', '')
    
    # Check if user has registered their location
    if user_id and user_id.isdigit():
        user_id_int = int(user_id)
        
        # Check pending shares first
        if user_id_int in pending_shares:
            share_data = pending_shares[user_id_int]
            if share_data.get('coords'):
                return jsonify({'coords': share_data['coords']})
        
        # Check database for latest location
        user = db.get_user(user_id=user_id_int)
        if user and user.get('last_location'):
            return jsonify({'coords': user['last_location']})
    
    # If no specific user location, try to find ANY user's last location
    # This is a fallback for when app uses 'app_user' as ID
    if user_id == 'app_user' or not user_id:
        try:
            # Get the most recent location from any user
            from pymongo import DESCENDING
            latest_user = db._db.users.find_one(
                {'last_location': {'$exists': True, '$ne': ''}},
                sort=[('location_updated_at', DESCENDING)]
            )
            if latest_user and latest_user.get('last_location'):
                return jsonify({'coords': latest_user['last_location']})
        except:
            pass
    
    return jsonify({'error': 'No location available'}), 404


@app.route('/api/update-location', methods=['POST'])
def update_user_location():
    """
    App sends its current location to the server
    Request body: {
        "user_id": "telegram_user_id",
        "coords": "lat,lng"
    }
    """
    data = request.json
    
    user_id = data.get('user_id', '')
    coords = data.get('coords', '')
    
    if not user_id or not coords:
        return jsonify({'success': False, 'error': 'Missing user_id or coords'})
    
    user_id_int = int(user_id) if str(user_id).isdigit() else 0
    
    # Update user's location in database
    db.update_user_location(user_id_int, coords)
    
    # Also update pending shares if any
    if user_id_int in pending_shares:
        pending_shares[user_id_int]['coords'] = coords
    
    return jsonify({'success': True})


@app.route('/api/submit-location', methods=['POST'])
def submit_location():
    """
    App sends location to this endpoint after bot requested it
    """
    data = request.json
    
    user_id = data.get('user_id', '')
    coords = data.get('coords', '')
    location_name = data.get('location_name', 'Current Location')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'Missing user_id'})
    
    user_id_int = int(user_id) if str(user_id).isdigit() else 0
    
    # Check if there's a pending request
    if user_id_int in pending_shares:
        share_data = pending_shares[user_id_int]
        if share_data.get('state') == 'waiting_location_from_app':
            # Location received from app!
            sender_id = share_data.get('sender_id')
            sender_name = share_data.get('sender_name', 'Unknown')
            friend_username = share_data.get('friend_username', '')
            
            # Clear pending request from app_user
            del pending_shares[user_id_int]
            
            if sender_id:
                if friend_username:
                    # We have friend's username - send location directly to friend
                    try:
                        # Get friend's chat_id
                        friend = db.get_user(username=friend_username)
                        if friend and friend.get('chat_id'):
                            chat_id = friend['chat_id']
                            maps_url = f"https://www.google.com/maps?q={coords}"
                            
                            share_message = f"""
ðŸ“ *Location Shared by Friend*

ðŸ‘¤ *From:* {sender_name}

ðŸ“ *Location:* {location_name}
ðŸ“Œ *Coordinates:* {coords}

ðŸ—ºï¸ [View on Google Maps]({maps_url})

_Sent via UOG Navigator Bot_
"""
                            loop = asyncio.get_event_loop()
                            loop.run_until_complete(application.bot.send_message(
                                chat_id=chat_id,
                                text=share_message,
                                parse_mode='Markdown'
                            ))
                            
                            # Notify sender
                            try:
                                import requests as req
                                req.post(
                                    f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
                                    json={
                                        'chat_id': sender_id,
                                        'text': f"âœ… *Location Sent!*\n\n"
                                            f"ðŸ“ Sent to @{friend_username}\n"
                                            f"ðŸ“Œ Coordinates: {coords}",
                                        'parse_mode': 'Markdown'
                                    }
                                )
                            except Exception as e:
                                logger.error(f"Error notifying sender: {e}")
                            
                            return jsonify({'success': True, 'message': f'Location sent to @{friend_username}!'})
                        else:
                            # Friend not found in database
                            try:
                                import requests as req
                                req.post(
                                    f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
                                    json={
                                        'chat_id': sender_id,
                                        'text': f"âŒ *Could not send location!*\n\n"
                                            f"User @{friend_username} has not started the bot yet.",
                                        'parse_mode': 'Markdown'
                                    }
                                )
                            except:
                                pass
                            return jsonify({'success': False, 'error': 'Friend has not started the bot'})
                    except Exception as e:
                        logger.error(f"Error sending location: {e}")
                        return jsonify({'success': False, 'error': str(e)})
                else:
                    # No friend_username - ask user
                    pending_shares[sender_id] = {
                        'state': 'waiting_username_with_location',
                        'coords': coords,
                        'sender_name': sender_name,
                        'timestamp': datetime.now()
                    }
                    
                    try:
                        import requests as req
                        req.post(
                            f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
                            json={
                                'chat_id': sender_id,
                                'text': f"ðŸ“ *Location Received from App!*\n\n"
                                    f"Your coordinates: {coords}\n\n"
                                    f"Now, please reply with your friend's Telegram username (without @) to share it.\n"
                                    f"Example: john_doe",
                                'parse_mode': 'Markdown'
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error asking for username: {e}")
                    
                    return jsonify({'success': True, 'message': 'Location received. Asking for username.'})
            
            return jsonify({'success': True, 'message': 'Location received.'})
    
    return jsonify({'success': False, 'error': 'No pending location request'})


@app.route('/api/instant-share', methods=['POST'])
def instant_share_location():
    """
    NEW: INSTANT LOCATION SHARE - Gets GPS from app and sends to friend immediately
    This bypasses the Telegram bot polling mechanism
    
    Request body: {
        "user_id": "telegram_user_id",
        "friend_username": "friend_username",
        "coords": "lat,lng",
        "location_name": "Location Name",
        "sender_name": "Sender Name"
    }
    """
    data = request.json
    
    user_id = data.get('user_id', '')
    friend_username = data.get('friend_username', '').strip().lower()
    coords = data.get('coords', '')
    location_name = data.get('location_name', 'My Current Location')
    sender_name = data.get('sender_name', 'A friend')
    
    if not friend_username or not coords:
        return jsonify({
            'success': False, 
            'error': 'Missing friend_username or coords'
        }), 400
    
    user_id_int = int(user_id) if str(user_id).isdigit() else 0
    
    # Clear any pending share for this user
    if user_id_int in pending_shares:
        del pending_shares[user_id_int]
    
    # Get friend's chat_id
    friend_chat_id = get_user_chat_id(friend_username)
    
    if not friend_chat_id:
        return jsonify({
            'success': False,
            'error': f'User @{friend_username} has not started the bot yet'
        }), 404
    
    # Create share record in MongoDB
    share_id = db.create_location_share(
        sender_id=user_id_int,
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
ðŸ“ *Location Shared by Friend*

ðŸ‘¤ *From:* {sender_name}

ðŸ“ *Location:* {location_name}
ðŸ“Œ *Coordinates:* {coords}

ðŸ—ºï¸ [View on Google Maps]({maps_url})

_Sent via UOG Navigator Bot_
"""
    
    # Send message to friend's Telegram IMMEDIATELY
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
        return jsonify({
            'success': False,
            'error': f'Failed to send to Telegram: {str(e)}'
        }), 500
    
    return jsonify({
        'success': True,
        'message': f'Location sent to @{friend_username} instantly!',
        'share_id': share_id,
        'share_details': {
            'to': friend_username,
            'coords': coords,
            'location_name': location_name,
            'maps_url': maps_url
        }
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
            InlineKeyboardButton("ðŸ“¤ Share Current Location", callback_data='share_location_start'),
        ],
        [
            InlineKeyboardButton("ðŸ« Maraki Campus", callback_data='campus_maraki'),
        ],
        [
            InlineKeyboardButton("ðŸ¢ Tewodros Campus", callback_data='campus_tewodros'),
        ],
        [
            InlineKeyboardButton("ðŸ¥ Fasil Campus", callback_data='campus_fasil'),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
ðŸ›ï¸ *Welcome to UOG Student Navigation Bot!*

I can help you navigate the University of Gondar campuses.

*What would you like to do?*
â€¢ ðŸ“¤ Share your current location with friends
â€¢ ðŸ« Explore campus locations and buildings
â€¢ ðŸ—ºï¸ Get directions to campus locations
"""
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_message = """
ðŸ“š *Available Commands:*

/start - Start the bot
/menu - Show main menu
/campuses - List all campuses
/locations - Show all locations
/buildings - Show only buildings
/cafes - Show only cafes
/libraries - Show only libraries

ðŸ“¤ *Share Location:*
Use /menu and click "Share My Location" button!

ðŸ”¹ *Campus Codes:*
â€¢ maraki - Main Campus
â€¢ tewodros - Tewodros Campus  
â€¢ fasil - Fasil Campus
"""
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def locations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all locations"""
    message = "ðŸ“ *All University Locations:*\n\n"
    
    # Get locations from MongoDB
    locations = db.get_campus_locations()
    if not locations:
        locations = CampusData.LOCATIONS  # Fallback to static
    
    for loc in locations:
        emoji = get_category_emoji(loc['category'])
        message += f"{emoji} *{loc['name']}*\n"
        message += f"   ðŸ“Œ {loc['campus'].title()} Campus\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu"""
    register_user(update)
    
    keyboard = [
        [
            InlineKeyboardButton("ðŸ“¤ Share Current Location", callback_data='share_location_start'),
        ],
        [
            InlineKeyboardButton("ðŸ« Maraki Campus", callback_data='campus_maraki'),
        ],
        [
            InlineKeyboardButton("ðŸ¢ Tewodros Campus", callback_data='campus_tewodros'),
        ],
        [
            InlineKeyboardButton("ðŸ¥ Fasil Campus", callback_data='campus_fasil'),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "ðŸ›ï¸ *UOG Student Navigation*\n\n*What would you like to do?*\nâ€¢ ðŸ“¤ Share your current location\nâ€¢ ðŸ« Explore campus locations",
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
                InlineKeyboardButton("ðŸ”™ Back to Campuses", callback_data='back_campuses')
            ])
            
            message = f"ðŸ›ï¸ *{campus_info.get('name', campus_id.title())} Campus*\n\n"
            message += f"ðŸ“Š Total locations: {len(locations)}\n\n"
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
                            f"ðŸ“ {loc['name']}", 
                            callback_data=f'location_{loc["name"]}'
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(f"ðŸ”™ Back", callback_data=f'campus_{campus_id}')
                ])
                
                message = f"{emoji} *{category_display} in {campus_info.get('name', campus_id.title())} Campus*\n\n"
                message += f"ðŸ“Š {len(locations)} location(s)\n\n"
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
ðŸ“ *{loc['name']}*

ðŸ›ï¸ Campus: {loc['campus'].title()}
ðŸ“ {loc['description']}
ðŸ“Œ Coordinates: {loc['coords']}

[ðŸ“ View on Google Maps]({maps_url})
"""
                
                await query.edit_message_text(
                    text=message,
                    parse_mode='Markdown'
                )
                break
    
    elif callback_data == 'back_campuses':
        keyboard = [
            [InlineKeyboardButton("ðŸ« Maraki Campus", callback_data='campus_maraki')],
            [InlineKeyboardButton("ðŸ¢ Tewodros Campus", callback_data='campus_tewodros')],
            [InlineKeyboardButton("ðŸ¥ Fasil Campus", callback_data='campus_fasil')],
        ]
        
        await query.edit_message_text(
            text="ðŸ›ï¸ *Select a Campus:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif callback_data == 'share_location_start':
        # Start share location flow - get location from app via API first
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # We put the request for user ID 0 so the hardcoded 'app_user' picks it up
        pending_shares[0] = {
            'state': 'waiting_location_from_app',
            'sender_id': user_id,
            'sender_name': username,
            'timestamp': datetime.now()
        }
        
        await query.edit_message_text(
            text="â³ *Waiting for location...*\n\n"
                "Please make sure the UOG Navigator app is open on your mobile device. I will automatically get your location coordinates.",
            parse_mode='Markdown'
        )
    
    elif callback_data.startswith('confirm_send_'):
        # Handle confirm send button click
        # Format: confirm_send_friend_username_coords
        parts = callback_data.replace('confirm_send_', '').split('_')
        if len(parts) >= 2:
            friend_username = parts[0]
            coords = '_'.join(parts[1:])  # In case coords has underscore
            
            sender_id = update.effective_user.id
            sender_name = update.effective_user.username or update.effective_user.first_name
            
            # Send location to friend
            try:
                # Get friend's chat_id from database
                friend = db.get_user(username=friend_username)
                if friend:
                    chat_id = friend.get('chat_id')
                    if chat_id:
                        # Generate maps link
                        lat, lng = coords.split(',')
                        maps_link = f"https://www.google.com/maps?q={lat},{lng}"
                        
                        # Send to friend
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"ðŸ“ *Location Shared by Friend*\n\n"
                                f"ðŸ“± *From:* @{sender_name}\n"
                                f"ðŸ“Œ *Coordinates:* {coords}\n"
                                f"ðŸ”— *Map Link:* {maps_link}",
                            parse_mode='Markdown'
                        )
                        
                        # Confirm to sender
                        await query.edit_message_text(
                            text=f"Location Sent Successfully!\n\n"
                                f"Location sent to: @{friend_username}\n"
                                f"Coordinates: {coords}\n\n"
                                f"Your friend has received the location link!"
                        )
                    else:
                        await query.edit_message_text(
                            text=f"Could not send to @{friend_username}.\n"
                                f"They may not have started the bot yet."
                        )
                else:
                    await query.edit_message_text(
                        text=f"User @{friend_username} not found!"
                    )
            except Exception as e:
                await query.edit_message_text(
                    text=f"âŒ Error sending location: {str(e)}",
                    parse_mode='Markdown'
                )
            
            # Clean up
            if sender_id in pending_shares:
                del pending_shares[sender_id]
            return
    
    elif callback_data == 'cancel_send':
        # Handle cancel button click
        user_id = update.effective_user.id
        if user_id in pending_shares:
            del pending_shares[user_id]
        
        await query.edit_message_text(
            text="âŒ *Share Location Cancelled*\n\n"
                "Your location was not sent to anyone.",
            parse_mode='Markdown'
        )
        return


async def handle_location_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location messages sent by users in server.py"""
    user_id = update.effective_user.id
    
    # Check if user is in share location flow
    if user_id in pending_shares:
        share_data = pending_shares[user_id]
        
        if share_data.get('state') == 'waiting_location':
            # Get the location from the message
            location = update.message.location
            lat = location.latitude
            lng = location.longitude
            coords = f"{lat},{lng}"
            
            # Clear the pending share
            del pending_shares[user_id]
            
            # Ask for friend's username
            await update.message.reply_text(
                f"ðŸ“ *Location Received!*\n\n"
                f"Your location: {coords}\n\n"
                f"Now please reply with your friend's Telegram username (without @)\n"
                f"Example: john_doe\n\n"
                f"âš ï¸ Your friend must have started the bot first!",
                parse_mode='Markdown'
            )
            
            # Store location for next message
            pending_shares[user_id] = {'state': 'waiting_username', 'coords': coords, 'timestamp': datetime.now()}
            return
        
        elif share_data.get('state') == 'waiting_location_from_app':
            # User sent location from Telegram - accept it and send to friend
            location = update.message.location
            lat = location.latitude
            lng = location.longitude
            coords = f"{lat},{lng}"
            
            friend_username = share_data.get('friend_username', '')
            sender_name = share_data.get('sender_name', username)
            
            # Get friend from database
            friend = db.get_user(username=friend_username)
            
            if not friend:
                await update.message.reply_text(
                    f"Could not find user @{friend_username}.",
                )
                del pending_shares[user_id]
                return
            
            # Generate maps link
            maps_link = f"https://www.google.com/maps?q={lat},{lng}"
            
            # Send location to friend
            try:
                await context.bot.send_message(
                    chat_id=friend['user_id'],
                    text=f"ðŸ“ *Location from @{sender_name}*\n\n"
                        f"ðŸ“± *From:* @{sender_name}\n"
                        f"ðŸ“Œ *Coordinates:* {coords}\n"
                        f"ðŸ”— *Map Link:* {maps_link}",
                    parse_mode='Markdown'
                )
                
                # Confirm to sender
                await update.message.reply_text(
                    text=f"Location Sent Successfully!\n\n"
                        f"Location sent to: @{friend_username}\n"
                        f"Coordinates: {coords}\n\n"
                        f"Your friend has received the location link!"
                )
            except Exception as e:
                await update.message.reply_text(
                    text=f"Could not send to @{friend_username}.\n"
                        f"They may not have started the bot yet."
                )
            
            # Clear pending share
            del pending_shares[user_id]
            return
    
    # If not in share mode, just acknowledge
    await update.message.reply_text(
        "ðŸ“ Thank you for sharing your location!\n\n"
        "Use /menu to see available options."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Check if user is in share location flow
    if user_id in pending_shares:
        share_data = pending_shares[user_id]
        
        if share_data.get('state') == 'waiting_friend_username':
            # User entered friend's username
            friend_username = text.strip()
            if friend_username.startswith('@'):
                friend_username = friend_username[1:]
            friend_username = friend_username.lower()
            
            # Check if friend exists in database
            friend = db.get_user(username=friend_username)
            
            if not friend:
                await update.message.reply_text(
                    f"âŒ User @{friend_username} not found!\n\n"
                    f"Please make sure your friend has started the bot first.\n"
                    f"Type /cancel to try again.",
                    parse_mode='Markdown'
                )
                return
            
            # Try to get location from app via API
            coords = None
            try:
                import requests
                # First try with user's actual ID
                response = requests.get(f'{os.getenv("APP_API_URL", "http://127.0.0.1:5000")}/api/get-current-location?user_id={user_id}', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    coords = data.get('coords')
                
                # If not found, try with 'app_user' as fallback
                if not coords:
                    response = requests.get(f'{os.getenv("APP_API_URL", "http://127.0.0.1:5000")}/api/get-current-location?user_id=app_user', timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        coords = data.get('coords')
            except:
                pass
            
            if coords:
                # Got location from app, send directly to friend
                lat, lng = coords.split(',') if coords else (0, 0)
                maps_link = f"https://www.google.com/maps?q={lat},{lng}"
                
                # Send location to friend
                try:
                    chat_id = friend.get('chat_id')
                    if chat_id:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"Location from @{username}\n\n"
                                f"Coordinates: {coords}\n"
                                f"Map: {maps_link}"
                        )
                        
                        # Confirm to sender
                        await update.message.reply_text(
                            text=f"Location sent to @{friend_username}!\n\n"
                                f"Coordinates: {coords}\n"
                                f"Map: {maps_link}"
                        )
                    else:
                        await update.message.reply_text(
                            text=f"Could not send to @{friend_username}. They may not have started the bot yet."
                        )
                except Exception as e:
                    await update.message.reply_text(
                        text=f"Error sending location: {str(e)}"
                    )
                
                # Clear pending share
                del pending_shares[user_id]
            else:
                # Can't get location from app, set state and tell user to open app
                pending_shares[user_id] = {
                    'state': 'waiting_location_from_app',
                    'friend_username': friend_username,
                    'sender_name': username,
                    'sender_id': user_id,  # Store the sender's Telegram ID
                    'timestamp': datetime.now()
                }
                
                # ALSO store for app_user (ID 0) so the app can pick it up when polling
                pending_shares[0] = {
                    'state': 'waiting_location_from_app',
                    'friend_username': friend_username,
                    'sender_name': username,
                    'sender_id': user_id,  # IMPORTANT: Store sender's Telegram ID so we can send to them later
                    'timestamp': datetime.now()
                }
                
                await update.message.reply_text(
                    f"Friend Found: @{friend_username}\n\n"
                        "ðŸ“± Please open the UOG Navigator app and share your location.\n\n"
                        "I'll automatically get your current location from the app and send it to your friend!",
                    parse_mode='Markdown'
                )
            return
        
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
                    f"âŒ User @{friend_username} not found!\n\n"
                    f"Please make sure your friend has started the bot first.",
                    parse_mode='Markdown'
                )
                del pending_shares[user_id]
                return
            
            # Get the location coordinates that was stored
            coords = share_data.get('coords', '')
            lat, lng = coords.split(',') if coords else (0, 0)
            
            # Generate Google Maps link
            maps_link = f"https://www.google.com/maps?q={lat},{lng}"
            
            # Send location directly to friend without asking for confirmation
            try:
                chat_id = friend.get('chat_id')
                if chat_id:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Location from @{username}\n\n"
                            f"Coordinates: {coords}\n"
                            f"Map: {maps_link}"
                    )
                    
                    # Confirm to sender
                    await update.message.reply_text(
                        text=f"Location sent to @{friend_username}!\n\n"
                            f"Coordinates: {coords}\n"
                            f"Map: {maps_link}"
                    )
                else:
                    await update.message.reply_text(
                        text=f"Could not send to @{friend_username}. They may not have started the bot yet."
                    )
            except Exception as e:
                await update.message.reply_text(
                    text=f"Error sending location: {str(e)}"
                )
            
            # Clear pending share
            del pending_shares[user_id]
            return
        
        elif share_data.get('state') == 'waiting_location':
            await update.message.reply_text(
                "Please send your location from Telegram using the attachment button, or click /cancel to cancel."
            )
            return
        
        if share_data.get('state') == 'waiting_username_with_location':
            # Got location from app, now user enters friend's username
            friend_username = text.strip()
            if friend_username.startswith('@'):
                friend_username = friend_username[1:]
            friend_username = friend_username.lower()
            
            # Check if friend exists in database
            friend = db.get_user(username=friend_username)
            
            if not friend:
                await update.message.reply_text(
                    f"User @{friend_username} not found!\n\n"
                    f"Please make sure your friend has started the bot first."
                )
                del pending_shares[user_id]
                return
            
            # Get the location coordinates that was stored
            coords = share_data.get('coords', '')
            lat, lng = coords.split(',') if coords else (0, 0)
            
            # Generate Google Maps link
            maps_link = f"https://www.google.com/maps?q={lat},{lng}"
            
            # Send location directly to friend
            try:
                chat_id = friend.get('chat_id')
                if chat_id:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Location from @{username}\n\n"
                            f"Coordinates: {coords}\n"
                            f"Map: {maps_link}"
                    )
                    
                    # Confirm to sender
                    await update.message.reply_text(
                        text=f"Location sent to @{friend_username}!\n\n"
                            f"Coordinates: {coords}\n"
                            f"Map: {maps_link}"
                    )
                else:
                    await update.message.reply_text(
                        text=f"Could not send to @{friend_username}. They may not have started the bot yet."
                    )
            except Exception as e:
                await update.message.reply_text(
                    text=f"Error sending location: {str(e)}"
                )
            
            # Clear pending share
            del pending_shares[user_id]
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
        await update.message.reply_text("âŒ Share location cancelled.")
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
                    f"ðŸ“ *{loc['name']}*\n\n"
                    f"Campus: {loc['campus'].title()}\n"
                    f"Coordinates: {loc['coords']}\n\n"
                    f"[View on Maps]({maps_url})",
                    parse_mode='Markdown'
                )
                return
        
        await update.message.reply_text(
            "â“ Use /locations to see all places or /help for commands."
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
    print("[DEBUG] Registering handlers...")
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('menu', menu_command))
    application.add_handler(CommandHandler('locations', locations_command))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location_message))
    print("[DEBUG] All handlers registered!")
    
    print("\n" + "="*50)
    print("UOG Student Navigation Server")
    print("="*50)
    print("Bot handlers registered")
    print(f"API available at: http://localhost:5000")
    print("="*50 + "\n")
    
    # Run Flask app (with bot polling OR webhook)
    # For webhook mode, you need to set WEBHOOK_URL environment variable
    webhook_url = os.getenv('WEBHOOK_URL')
    
    # On Render (or production), use webhook mode by default
    # Check if we're running on a cloud platform
    is_production = os.getenv('RENDER') or os.getenv('PORT')
    
    if webhook_url or is_production:
        # Webhook mode (preferred for production like Render)
        # Use webhook URL from env or construct one based on RENDERExternalURL
        if not webhook_url:
            render_url = os.getenv('RENDER_EXTERNAL_URL')
            if render_url:
                webhook_url = f"{render_url}/webhook"
        
        if webhook_url:
            print(f"Using webhook mode: {webhook_url}")
            application.run_webhook(
                listen='0.0.0.0',
                port=int(os.getenv('PORT', 5000)),
                url_path='webhook',
                webhook_url=webhook_url
            )
        else:
            # Fallback to polling if no webhook URL available
            print("No webhook URL available, using polling mode")
            application.run_polling(drop_pending_updates=True)
    else:
        # Polling mode (for local development)
        # Start Flask in background thread
        import threading
        flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, threaded=True))
        flask_thread.daemon = True
        flask_thread.start()
        
        # Run bot with polling - drop pending updates to avoid conflicts
        application.run_polling(drop_pending_updates=True)


# ============================================================================
# AI CHAT ASSISTANT ROUTES
# ============================================================================

# Import AI service
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from ai_service_template import AICampusAssistant
    ai_assistant = AICampusAssistant(provider="aipipe")
    print("âœ“ AI Campus Assistant initialized with AIPIPE API")
except Exception as e:
    print(f"âœ— AI Assistant initialization failed: {e}")
    ai_assistant = None

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Main AI chat endpoint for campus assistant"""
    global ai_assistant
    from flask import request, jsonify
    
    # Debug: Check if AI assistant is available
    print(f"[DEBUG] AI Chat request received, ai_assistant type: {type(ai_assistant)}")
    
    if ai_assistant is None:
        print("[DEBUG] AI Assistant is None, attempting to reinitialize...")
        # Try to reinitialize
        try:
            from ai_service_template import AICampusAssistant
            ai_assistant = AICampusAssistant(provider="aipipe")
            print(f"[DEBUG] AI reinitialized, provider: {ai_assistant.provider}")
        except Exception as e:
            print(f"[DEBUG] Failed to reinitialize AI: {e}")
            return jsonify({
                'success': False,
                'error': 'AI Assistant not available',
                'details': str(e)
            }), 500
    
    # Check if provider is fallback (meaning API token wasn't found)
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


@app.route('/api/ai/health', methods=['GET'])
def ai_health():
    """Health check for AI endpoint - useful for debugging connectivity"""
    from flask import jsonify
    
    status = {
        'status': 'ok',
        'ai_available': ai_assistant is not None,
        'provider': ai_assistant.provider if ai_assistant else 'none',
        'token_available': bool(ai_assistant.aipipe_token) if ai_assistant and hasattr(ai_assistant, 'aipipe_token') else False
    }
    
    return jsonify(status)

@app.route('/api/ai/suggestions', methods=['GET'])
def ai_suggestions():
    """Get suggested questions for quick actions"""
    from flask import jsonify
    
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

@app.route('/api/ai/clear', methods=['POST'])
def ai_clear():
    """Clear conversation history"""
    from flask import jsonify
    
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


if __name__ == '__main__':
    import asyncio
    main()
