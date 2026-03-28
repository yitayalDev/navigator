"""
Flask App Factory
Creates and configures the Flask application
"""
import os
import sys
from pathlib import Path
from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from bson import ObjectId

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_app():
    """Create and configure the Flask application"""
    # Create Flask app
    template_path = Path(__file__).parent.parent / 'templates'
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
    
    # Register blueprints
    from flask_app.routes import admin, api, ai
    
    # Register admin blueprint
    app.register_blueprint(admin.admin_bp, url_prefix='/admin')
    
    # Register API blueprints
    app.register_blueprint(api.api_bp, url_prefix='/api')
    app.register_blueprint(ai.ai_bp, url_prefix='/api/ai')
    
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
        flutter_build_path = Path(__file__).parent.parent.parent / 'frontend' / 'build' / 'web'
        
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
        from flask import send_file, abort
        import mimetypes
        flutter_build_path = Path(__file__).parent.parent.parent / 'frontend' / 'build' / 'web'
        file_path = flutter_build_path / filename
        
        if file_path.exists():
            content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            with open(file_path, 'rb') as f:
                return f.read(), 200, {'Content-Type': content_type}
        else:
            return "File not found", 404
    
    return app


def get_app():
    """Get the Flask app instance (alias for create_app)"""
    return create_app()