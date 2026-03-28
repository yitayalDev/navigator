"""
Admin Routes Blueprint
Contains all admin panel routes for login, dashboard, buildings, categories, and campuses
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Blueprint, render_template, redirect, request, jsonify, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

# Import database and config
from services.database import db
from utils.config import CampusData


# Create blueprint
admin_bp = Blueprint('admin', __name__)


# User class for Flask-Login (shared with main app)
class User:
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username
    
    def get_id(self):
        return str(self.id)


# User loader (will be registered with app)
@admin_bp.before_app_request
def load_user():
    """Load user for Flask-Login"""
    pass


def get_categories_list():
    """Get categories list with fallback to default categories."""
    try:
        if db.is_connected():
            categories = db.get_all_categories()
            if categories:
                return categories
        return ['building', 'administration', 'library', 'lab', 'cafe', 'dorm', 'lecture_hall']
    except Exception as e:
        print(f"Error getting categories: {e}")
        return ['building', 'administration', 'library', 'lab', 'cafe', 'dorm', 'lecture_hall']


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
        print(f"Error getting campuses for template: {e}")
        return CampusData.CAMPUSES


# Login route
@admin_bp.route('/login', methods=['GET', 'POST'])
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


# Logout route
@admin_bp.route('/logout')
@login_required
def logout():
    """Admin logout."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect('/admin/login')


# Dashboard route
@admin_bp.route('/', methods=['GET'])
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
    
    # Get campus counts
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


# Buildings routes
@admin_bp.route('/buildings', methods=['GET'])
@login_required
def admin_buildings():
    """Manage buildings page."""
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    campus = request.args.get('campus', '')
    
    per_page = 20
    
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


@admin_bp.route('/buildings/add', methods=['GET', 'POST'])
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
            
            if not name or not category or not campus or not coords:
                return render_template('admin/building_form.html',
                    active_page='buildings',
                    building=None,
                    categories_list=get_categories_list(),
                    campuses=get_campuses_for_template(),
                    error='All fields are required'
                )
            
            result = db.add_building(
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
                    error='Failed to add building - check server logs'
                )
        except Exception as e:
            print(f"Error adding building: {e}")
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


@admin_bp.route('/buildings/edit/<building_id>', methods=['GET', 'POST'])
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
            print(f"Error updating building: {e}")
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


@admin_bp.route('/api/buildings/<building_id>', methods=['DELETE'])
@login_required
def admin_delete_building(building_id):
    """API endpoint to delete a building."""
    result = db.delete_building(building_id)
    return jsonify({
        'success': result,
        'message': 'Building deleted successfully' if result else 'Failed to delete building'
    })


# Categories routes
@admin_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    """Categories management page."""
    try:
        category_counts = db.get_building_count_by_category()
        cat_dict = {c['_id']: c['count'] for c in category_counts}
        
        custom_cats = list(db._db.categories.find({}, {'name': 1, 'description': 1, 'icon': 1, 'color': 1}))
        
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
        
        categories = sorted(categories, key=lambda x: x['name'])
    except Exception as e:
        print(f"Error loading categories: {e}")
        categories = []
        cat_dict = {}
    
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
            print(f"Error adding category: {e}")
            flash(f'Error adding category: {str(e)}', 'danger')
        
        return redirect('/admin/categories')
    
    return render_template('admin/categories.html',
        active_page='categories',
        categories=categories,
        category_counts=cat_dict
    )


@admin_bp.route('/categories/delete/<category_name>', methods=['POST'])
@login_required
def delete_category(category_name):
    """Delete a category."""
    success = db.delete_category(category_name)
    if success:
        flash(f'Category "{category_name}" deleted successfully!', 'success')
    else:
        flash(f'Failed to delete category "{category_name}"!', 'danger')
    return redirect('/admin/categories')


# Campuses routes
@admin_bp.route('/campuses', methods=['GET', 'POST'])
@login_required
def admin_campuses():
    """Campuses management page."""
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
            print(f"Error adding campus: {e}")
            flash(f'Error adding campus: {str(e)}', 'danger')
        
        return redirect('/admin/campuses')
    
    db_campuses = db.get_all_campuses()
    campus_counts = db.get_building_count_by_campus()
    
    camp_data = []
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


@admin_bp.route('/campuses/delete/<campus_id>', methods=['POST'])
@login_required
def delete_campus(campus_id):
    """Delete a campus."""
    success = db.delete_campus(campus_id)
    if success:
        flash(f'Campus "{campus_id}" deleted successfully!', 'success')
    else:
        flash(f'Failed to delete campus "{campus_id}"!', 'danger')
    return redirect('/admin/campuses')