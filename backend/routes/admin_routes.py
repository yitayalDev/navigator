"""
Admin Routes Module
Handles all admin panel routes for campus/building/category management
"""
from flask import render_template, redirect, request, flash, jsonify
from flask_login import login_required
import logging

from services.sms_service import sms_service

logger = logging.getLogger(__name__)


def register_admin_routes(app, db, get_categories_list, get_campuses_for_template):
    """Register admin routes with the Flask app."""
    
    # Default categories for the admin panel
    DEFAULT_CATEGORIES = ['building', 'administration', 'library', 'lab', 'cafe', 'dorm', 'lecture_hall']
    
    # Secret route to reset password (no auth needed)
    @app.route('/admin/secret-reset', methods=['POST'])
    def secret_reset_password():
        """Directly reset admin password - no verification needed"""
        data = request.get_json() or {}
        new_password = data.get('password', 'admin123')
        
        if db.update_admin_password('admin123', new_password):
            return jsonify({'success': True, 'message': 'Password reset successfully'})
        return jsonify({'success': False, 'message': 'Failed to reset password'})
    
    @app.route('/admin/login', methods=['GET', 'POST'])
    def login():
        from flask_login import current_user, login_user
        from flask_bcrypt import Bcrypt
        
        if current_user.is_authenticated:
            return redirect('/admin')
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                return render_template(
                    'admin/login.html',
                    error='Please enter both username and password',
                    campuses=get_campuses_for_template()
                )
            
            # Find admin user
            user = db.get_admin_user(username)
            if user and user.get('password') and Bcrypt().check_password_hash(user['password'], password):
                user_obj = app.login_manager._user_callback(str(user['_id']))
                login_user(user_obj)
                
                next_page = request.args.get('next')
                return redirect(next_page or '/admin')
            else:
                return render_template(
                    'admin/login.html',
                    error='Invalid username or password',
                    campuses=get_campuses_for_template()
                )
        
        return render_template('admin/login.html', campuses=get_campuses_for_template())

    @app.route('/admin/logout')
    @login_required
    def logout():
        from flask_login import logout_user
        logout_user()
        flash('You have been logged out', 'info')
        return redirect('/admin/login')

    # ============================================================================
    # PASSWORD RESET ROUTES (SMS-based)
    # ============================================================================

    @app.route('/admin/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        """Step 1: Enter username to request SMS reset."""
        from flask_login import current_user
        
        if current_user.is_authenticated:
            return redirect('/admin')
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            
            if not username:
                return render_template(
                    'admin/forgot_password.html',
                    error='Please enter your username',
                    campuses=get_campuses_for_template()
                )
            
            # Check if user exists
            user = db.get_admin_user(username)
            logger.info(f"[DEBUG] get_admin_user returned: {user}")
            if not user:
                return render_template(
                    'admin/forgot_password.html',
                    error='User not found',
                    campuses=get_campuses_for_template()
                )
            
            # Check if user has phone number
            phone = user.get('phone_number', user.get('phone', ''))
            logger.info(f"[DEBUG] Phone value: '{phone}' | Type: {type(phone)}")
            if not phone:
                return render_template(
                    'admin/forgot_password.html',
                    error='No phone number associated with this account. Please contact administrator.',
                    campuses=get_campuses_for_template()
                )
            
            # Generate code and store in database
            code = sms_service.generate_verification_code()
            
            # Store in database
            if not db.create_sms_verification(username, phone, code):
                return render_template(
                    'admin/forgot_password.html',
                    error='Failed to create verification. Please try again.',
                    campuses=get_campuses_for_template()
                )
            
            # Send SMS
            if sms_service.send_verification_code(phone, code, username):
                # Store username in session for verification step
                from flask import session
                session['reset_username'] = username
                flash('Verification code sent to your phone!', 'success')
                return redirect('/admin/verify-code')
            else:
                return render_template(
                    'admin/forgot_password.html',
                    error='Failed to send SMS. Please try again.',
                    campuses=get_campuses_for_template()
                )
        
        return render_template('admin/forgot_password.html', campuses=get_campuses_for_template())

    @app.route('/admin/verify-code', methods=['GET', 'POST'])
    def verify_code():
        """Step 2: Enter verification code from SMS."""
        from flask_login import current_user
        from flask import session
        
        if current_user.is_authenticated:
            return redirect('/admin')
        
        username = session.get('reset_username')
        if not username:
            flash('Please start the password reset process', 'warning')
            return redirect('/admin/forgot-password')
        
        if request.method == 'POST':
            code = request.form.get('code', '').strip()
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not code or not new_password or not confirm_password:
                return render_template(
                    'admin/verify_code.html',
                    error='Please fill in all fields',
                    username=username,
                    campuses=get_campuses_for_template()
                )
            
            if new_password != confirm_password:
                return render_template(
                    'admin/verify_code.html',
                    error='Passwords do not match',
                    username=username,
                    campuses=get_campuses_for_template()
                )
            
            if len(new_password) < 6:
                return render_template(
                    'admin/verify_code.html',
                    error='Password must be at least 6 characters',
                    username=username,
                    campuses=get_campuses_for_template()
                )
            
            # Verify the code
            if db.verify_sms_code(username, code):
                # Update password
                if db.update_admin_password(username, new_password):
                    session.pop('reset_username', None)
                    flash('Password updated successfully! You can now login.', 'success')
                    return redirect('/admin/login')
                else:
                    return render_template(
                        'admin/verify_code.html',
                        error='Failed to update password. Please try again.',
                        username=username,
                        campuses=get_campuses_for_template()
                    )
            else:
                # Increment failed attempts
                attempts = db.increment_sms_attempts(username)
                error_msg = 'Invalid or expired verification code'
                if attempts >= 3:
                    error_msg = 'Too many failed attempts. Please request a new code.'
                    session.pop('reset_username', None)
                return render_template(
                    'admin/verify_code.html',
                    error=error_msg,
                    username=username,
                    campuses=get_campuses_for_template()
                )
        
        return render_template('admin/verify_code.html', username=username, campuses=get_campuses_for_template())

    @app.route('/admin', methods=['GET'])
    @login_required
    def admin_dashboard():
        try:
            stats = {
                'total_buildings': db.get_locations_count(),
                'total_campuses': len(db.get_all_campuses()),
                'total_users': len(db.get_all_users())
            }
            return render_template(
                'admin/index.html',
                stats=stats,
                campuses=get_campuses_for_template()
            )
        except Exception as e:
            logger.error(f"Error loading admin dashboard: {e}")
            return render_template('admin/index.html', stats={}, error=str(e), campuses=get_campuses_for_template())

    @app.route('/admin/buildings', methods=['GET'])
    @login_required
    def admin_buildings():
        try:
            buildings = db.get_all_locations()
            campuses = get_campuses_for_template()
            categories = get_categories_list()
            return render_template(
                'admin/buildings.html',
                buildings=buildings,
                categories=categories,
                campuses=campuses
            )
        except Exception as e:
            logger.error(f"Error loading buildings: {e}")
            return render_template('admin/buildings.html', buildings=[], categories=[], error=str(e), campuses=get_campuses_for_template())

    @app.route('/admin/buildings/add', methods=['GET', 'POST'])
    @login_required
    def admin_add_building():
        categories = get_categories_list()
        campuses = get_campuses_for_template()
        
        if request.method == 'POST':
            try:
                name = request.form.get('name')
                description = request.form.get('description', '')
                category = request.form.get('category', 'building')
                campus_id = request.form.get('campus_id')
                floor = request.form.get('floor')
                lat = request.form.get('latitude')
                lng = request.form.get('longitude')
                
                if not name or not campus_id:
                    return render_template(
                        'admin/building_form.html',
                        categories=categories,
                        campuses=campuses,
                        error='All fields are required'
                    )
                
                result = db.add_location(
                    name=name,
                    description=description,
                    category=category,
                    campus_id=campus_id,
                    floor=int(floor) if floor else 1,
                    latitude=float(lat) if lat else None,
                    longitude=float(lng) if lng else None
                )
                
                if result:
                    logger.info(f"Building added successfully: {name}")
                    return redirect('/admin/buildings')
                else:
                    return render_template(
                        'admin/building_form.html',
                        categories=categories,
                        campuses=campuses,
                        error='Failed to add building - check server logs'
                    )
            except Exception as e:
                logger.error(f"Error adding building: {e}")
                return render_template(
                    'admin/building_form.html',
                    categories=categories,
                    campuses=campuses,
                    error=f'Error: {str(e)}'
                )
        
        return render_template('admin/building_form.html', categories=categories, campuses=campuses)

    @app.route('/admin/buildings/edit/<building_id>', methods=['GET', 'POST'])
    @login_required
    def admin_edit_building(building_id):
        from bson import ObjectId
        categories = get_categories_list()
        campuses = get_campuses_for_template()
        
        building = db.get_location(ObjectId(building_id))
        if not building:
            return redirect('/admin/buildings')
        
        if request.method == 'POST':
            try:
                name = request.form.get('name')
                description = request.form.get('description', '')
                category = request.form.get('category', 'building')
                campus_id = request.form.get('campus_id')
                floor = request.form.get('floor')
                lat = request.form.get('latitude')
                lng = request.form.get('longitude')
                
                result = db.update_location(
                    ObjectId(building_id),
                    name=name,
                    description=description,
                    category=category,
                    campus_id=campus_id,
                    floor=int(floor) if floor else 1,
                    latitude=float(lat) if lat else None,
                    longitude=float(lng) if lng else None
                )
                
                if result:
                    logger.info(f"Building updated: {name}")
                    return redirect('/admin/buildings')
                else:
                    return render_template(
                        'admin/building_form.html',
                        categories=categories,
                        campuses=campuses,
                        building=building,
                        error='Failed to update building'
                    )
            except Exception as e:
                logger.error(f"Error updating building: {e}")
                return render_template(
                    'admin/building_form.html',
                    categories=categories,
                    campuses=campuses,
                    building=building,
                    error=f'Error: {str(e)}'
                )
        
        return render_template('admin/building_form.html', categories=categories, campuses=campuses, building=building)

    @app.route('/admin/api/buildings/<building_id>', methods=['DELETE'])
    @login_required
    def admin_delete_building(building_id):
        from bson import ObjectId
        try:
            result = db.delete_location(ObjectId(building_id))
            if result:
                logger.info(f"Building deleted: {building_id}")
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Failed to delete'}), 400
        except Exception as e:
            logger.error(f"Error deleting building: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/categories', methods=['GET', 'POST'])
    @login_required
    def admin_categories():
        categories = get_categories_list()
        campuses = get_campuses_for_template()
        
        if request.method == 'POST':
            new_category = request.form.get('new_category', '').strip().lower()
            if new_category and new_category not in categories:
                try:
                    db.add_category(new_category)
                    flash(f'Category "{new_category}" added successfully!', 'success')
                    logger.info(f"Category added: {new_category}")
                except Exception as e:
                    flash(f'Failed to add category: {str(e)}', 'danger')
                    logger.error(f"Error adding category: {e}")
            else:
                flash('Category already exists or invalid name', 'warning')
            return redirect('/admin/categories')
        
        return render_template('admin/categories.html', categories=categories, campuses=campuses)

    @app.route('/admin/categories/delete/<category_name>', methods=['POST'])
    @login_required
    def delete_category(category_name):
        try:
            db.delete_category(category_name)
            flash(f'Category "{category_name}" deleted successfully!', 'success')
            logger.info(f"Category deleted: {category_name}")
        except Exception as e:
            flash(f'Failed to delete category "{category_name}"!', 'danger')
            logger.error(f"Error deleting category: {e}")
        return redirect('/admin/categories')

    @app.route('/admin/campuses', methods=['GET', 'POST'])
    @login_required
    def admin_campuses():
        campuses = get_campuses_for_template()
        
        if request.method == 'POST':
            campus_name = request.form.get('name', '').strip()
            campus_code = request.form.get('code', '').strip()
            description = request.form.get('description', '').strip()
            default_center_lat = request.form.get('default_center_lat')
            default_center_lng = request.form.get('default_center_lng')
            default_zoom = request.form.get('default_zoom')
            
            if campus_name and campus_code:
                try:
                    result = db.add_campus(
                        name=campus_name,
                        code=campus_code,
                        description=description,
                        default_center_lat=float(default_center_lat) if default_center_lat else 55.8738,
                        default_center_lng=float(default_center_lng) if default_center_lng else -4.4136,
                        default_zoom=int(default_zoom) if default_zoom else 15
                    )
                    if result:
                        flash(f'Campus "{campus_name}" added successfully!', 'success')
                        logger.info(f"Campus added: {campus_name}")
                    else:
                        flash('Failed to add campus - code might already exist', 'danger')
                except Exception as e:
                    flash(f'Failed to add campus: {str(e)}', 'danger')
                    logger.error(f"Error adding campus: {e}")
            else:
                flash('Campus name and code are required', 'warning')
            return redirect('/admin/campuses')
        
        return render_template('admin/campuses.html', campuses=campuses)

    @app.route('/admin/campuses/delete/<campus_id>', methods=['POST'])
    @login_required
    def delete_campus(campus_id):
        from bson import ObjectId
        try:
            db.delete_campus(ObjectId(campus_id))
            flash(f'Campus deleted successfully!', 'success')
            logger.info(f"Campus deleted: {campus_id}")
        except Exception as e:
            flash(f'Failed to delete campus "{campus_id}"!', 'danger')
            logger.error(f"Error deleting campus: {e}")
        return redirect('/admin/campuses')

    logger.info("Admin routes registered successfully")