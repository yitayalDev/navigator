"""
UOG Student Navigation Flask Server
Handles API requests from the mobile app

This is the main entry point that routes to modular components:
- routes/admin_routes.py - Admin panel routes
- routes/api_routes.py - REST API routes
"""
import os
import sys
import mimetypes
from pathlib import Path
import logging

# Enable error logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import config and services
from utils.config import config, CampusData
from services.database import db

# Import modular routes
from routes.admin_routes import register_admin_routes
from routes.api_routes import register_api_routes


# ============================================================================
# FLASK APP FACTORY
# ============================================================================

def create_app():
    """Create and configure the Flask application."""
    from flask import Flask
    from flask_cors import CORS
    from flask_login import LoginManager, UserMixin
    from flask_bcrypt import Bcrypt
    from bson import ObjectId
    
    # Create Flask app
    template_path = Path(__file__).parent / 'templates'
    app = Flask(__name__, template_folder=str(template_path))
    app.secret_key = 'uog-navigator-admin-secret-key'
    
    # Initialize extensions
    CORS(app)
    bcrypt = Bcrypt(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Custom JSON encoder to handle ObjectId
    class MongoJSONProvider(app.json_provider_class):
        def default(self, obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            return super().default(obj)
    
    app.json_provider = MongoJSONProvider(app)
    app.json = app.json_provider
    
    # Store extensions in app for use in routes
    app.bcrypt = bcrypt
    app.login_manager = login_manager
    
    # Helper functions for routes
    def get_categories_list():
        """Get categories list with fallback to default categories."""
        DEFAULT_CATEGORIES = ['building', 'administration', 'library', 'lab', 'cafe', 'dorm', 'lecture_hall']
        try:
            if db.is_connected():
                categories = db.get_all_categories()
                if categories:
                    return categories
            return DEFAULT_CATEGORIES
        except:
            return DEFAULT_CATEGORIES
    
    def get_campuses_for_template():
        """Get campuses formatted for templates."""
        try:
            return db.get_all_campuses()
        except:
            return []
    
    # Register modular routes
    register_admin_routes(app, db, get_categories_list, get_campuses_for_template)
    register_api_routes(app, db)
    
    # Root route - redirect to admin
    @app.route('/')
    def index():
        from flask import redirect
        return redirect('/admin')
    
    # Serve Flutter web app from /app route
    @app.route('/app')
    def serve_flutter_app():
        """Serve the Flutter web app"""
        from flask import send_file, abort
        import mimetypes
        flutter_build_path = Path(__file__).parent.parent / 'frontend' / 'build' / 'web'
        
        index_path = flutter_build_path / 'index.html'
        if index_path.exists():
            with open(index_path, 'r') as f:
                content = f.read()
            content = content.replace('<base href="/">', '<base href="/app/">')
            return content
        else:
            return "Flutter app not found. Please run 'flutter build web' first.", 404
    
    @app.route('/app/<path:filename>')
    def serve_flutter_static(filename):
        """Serve static files from Flutter build"""
        from flask import send_file, abort
        import mimetypes
        flutter_build_path = Path(__file__).parent.parent / 'frontend' / 'build' / 'web'
        file_path = flutter_build_path / filename
        
        if file_path.exists():
            content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            with open(file_path, 'rb') as f:
                return f.read(), 200, {'Content-Type': content_type}
        else:
            return "File not found", 404
    
    return app


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to run the server."""
    from flask_login import UserMixin
    from bson import ObjectId
    
    # Validate config
    if not config.validate():
        print("\n" + "="*50)
        print("ERROR: Configuration is incomplete!")
        print("="*50)
        sys.exit(1)
    
    # Connect to MongoDB
    print("\n" + "="*50)
    print("Connecting to MongoDB...")
    print("="*50)
    
    if not db.connect():
        print("\n" + "="*50)
        print("WARNING: Could not connect to MongoDB!")
        print("The server will run but some features may not work.")
        print("="*50 + "\n")
    else:
        # Initialize default locations if database is empty
        existing_locations = db.get_campus_locations()
        if not existing_locations:
            print("No locations found in database. Initializing default locations...")
            db.initialize_default_locations()
        else:
            print(f"Found {len(existing_locations)} locations in database.")
        
        # Initialize default admin user
        print("Initializing default admin user...")
        if db.initialize_default_admin('admin123', '123'):
            print("Default admin user created: admin123")
    
    # Create and configure Flask app
    app = create_app()
    
    # User class for Flask-Login
    class User(UserMixin):
        def __init__(self, user_id, username):
            self.id = user_id
            self.username = username
        
        def get_id(self):
            return str(self.id)
    
    login_manager = app.login_manager
    
    @login_manager.user_loader
    def load_user(user_id):
        try:
            user = db._db.admin_users.find_one({'_id': ObjectId(user_id)})
            if user:
                return User(str(user['_id']), user['username'])
        except:
            user = db.get_admin_user(user_id)
            if user:
                return User(str(user['_id']), user['username'])
        return None
    
    print("\n" + "="*50)
    print("UOG Student Navigation Server")
    print("="*50)
    print("Flask API Server - Telegram Bot Disabled")
    
    # Determine the correct URL based on environment
    port = int(os.getenv('PORT', 5000))
    render_url = os.getenv('RENDER_EXTERNAL_URL')
    
    if render_url:
        api_url = render_url
    else:
        api_url = f"http://localhost:{port}"
    
    print(f"API available at: {api_url}")
    print(f"Admin panel at: {api_url}/admin")
    print("="*50 + "\n")
    
    # Start Flask API server
    print(f"Starting Flask API server on port {port}...")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )


if __name__ == '__main__':
    main()
