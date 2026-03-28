"""
UOG Student Navigation - Main Application Entry Point
Combines Flask server with Telegram bot
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Configure logging
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
from flask_app import create_app


# Global variables
application = None
pending_shares = {}  # Store pending location share requests
ai_assistant = None


def initialize_ai():
    """Initialize the AI assistant"""
    global ai_assistant
    try:
        from ai_service_template import AICampusAssistant
        ai_assistant = AICampusAssistant(provider="aipipe")
        print("✓ AI Campus Assistant initialized with AIPIPE API")
    except Exception as e:
        print(f"✗ AI Assistant initialization failed: {e}")
        ai_assistant = None
    
    return ai_assistant


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
    
    # Debug: Print environment variables
    mongo_uri_env = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI') or os.getenv('MONGODB_URL')
    mongo_db_env = os.getenv('MONGODB_DB_NAME') or os.getenv('MONGO_DB') or os.getenv('MONGODB_DATABASE')
    
    print(f"MONGODB_URI env: {os.getenv('MONGODB_URI')}")
    print(f"MONGO_URI env: {os.getenv('MONGO_URI')}")
    print(f"MONGODB_URL env: {os.getenv('MONGODB_URL')}")
    print(f"Final MongoDB URI being used: {mongo_uri_env}")
    print(f"Final MongoDB DB being used: {mongo_db_env}")
    print(f"Config MONGODB_URI: {config.MONGODB_URI}")
    print(f"Config MONGODB_DB_NAME: {config.MONGODB_DB_NAME}")
    
    if not db.connect():
        print("\n" + "="*50)
        print("WARNING: Could not connect to MongoDB!")
        print("The server will run but location sharing may not work.")
        print("Make sure MongoDB is running and configured in .env")
        print("="*50 + "\n")
    else:
        # Initialize default locations if database is empty
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
    
    # Initialize AI assistant
    initialize_ai()
    
    # Build Telegram application
    bot_token = config.get_bot_token()
    from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
    application = ApplicationBuilder().token(bot_token).build()
    
    # Add handlers - import from bot module
    from bot.handlers import start_command, help_command, locations_command, menu_command
    from bot.callbacks import callback_handler, handle_location_message, handle_message, set_pending_shares
    
    # Set pending shares reference in callbacks module
    set_pending_shares(pending_shares)
    
    print("[DEBUG] Registering handlers...")
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('menu', menu_command))
    application.add_handler(CommandHandler('locations', locations_command))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location_message))
    print("[DEBUG] All handlers registered!")
    
    # Set up Flask app
    app = create_app()
    
    # Fix template path for admin routes
    app.template_folder = str(Path(__file__).parent / 'templates')
    
    # Connect user loader for Flask-Login
    from flask_login import LoginManager
    from flask_bcrypt import Bcrypt
    from flask_login import UserMixin
    
    class User(UserMixin):
        def __init__(self, user_id, username):
            self.id = user_id
            self.username = username
        
        def get_id(self):
            return str(self.id)
    
    login_manager = app.login_manager
    
    @login_manager.user_loader
    def load_user(user_id):
        from bson import ObjectId
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
    print("Bot handlers registered")
    
    # Determine the correct URL based on environment
    port = int(os.getenv('PORT', 5000))
    render_url = os.getenv('RENDER_EXTERNAL_URL')
    
    if render_url:
        api_url = render_url
    else:
        api_url = f"http://localhost:{port}"
    
    print(f"API available at: {api_url}")
    print("="*50 + "\n")
    
    # Check environment
    is_production = os.getenv('RENDER') or os.getenv('PORT')
    
    # Print mode being used
    print("=" * 50)
    if is_production:
        print("PRODUCTION MODE DETECTED - Using polling mode")
    else:
        print("DEVELOPMENT MODE - Using polling mode")
    print("=" * 50 + "\n")
    
    # Start Flask API server in background thread
    import threading
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
    )
    flask_thread.daemon = True
    flask_thread.start()
    
    print(f"Flask API started on port {port}")
    
    # Use polling mode (not webhook - more reliable on cloud)
    print("Starting Telegram bot in polling mode...")
    application.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()