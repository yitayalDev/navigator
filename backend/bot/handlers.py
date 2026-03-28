"""
Telegram Bot Command Handlers
Contains async handlers for bot commands: start, help, menu, locations
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Import from services and utils
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.database import db
from utils.config import CampusData


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    register_user(update)
    
    keyboard = [
        [
            InlineKeyboardButton("📤 Share Current Location", callback_data='share_location_start'),
        ],
        [
            InlineKeyboardButton("🏫 Maraki Campus", callback_data='campus_maraki'),
        ],
        [
            InlineKeyboardButton("🏢 Tewodros Campus", callback_data='campus_tewodros'),
        ],
        [
            InlineKeyboardButton("🏰 Fasil Campus", callback_data='campus_fasil'),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
🏛️ *Welcome to UOG Student Navigation Bot!*

I can help you navigate the University of Gondar campuses.

*What would you like to do?*
• 📤 Share your current location with friends
• 🏫 Explore campus locations and buildings
• 📍 Get directions to campus locations
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

🔢 *Campus Codes:*
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
    """Show main menu"""
    register_user(update)
    
    keyboard = [
        [
            InlineKeyboardButton("📤 Share Current Location", callback_data='share_location_start'),
        ],
        [
            InlineKeyboardButton("🏫 Maraki Campus", callback_data='campus_maraki'),
        ],
        [
            InlineKeyboardButton("🏢 Tewodros Campus", callback_data='campus_tewodros'),
        ],
        [
            InlineKeyboardButton("🏰 Fasil Campus", callback_data='campus_fasil'),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏛️ *UOG Student Navigation*\n\n*What would you like to do?*\n• 📤 Share your current location\n• 🏫 Explore campus locations",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


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


def get_category_emoji(category: str) -> str:
    """Get emoji for category."""
    emojis = {
        'building': '🏢',
        'cafe': '☕',
        'library': '📚',
        'lecture_hall': '🎓',
        'lab': '🔬',
        'laboratory': '🔬',
        'administration': '🏛️',
        'dorm': '🏠'
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
        'laboratory': 'Laboratories',
        'administration': 'Administration',
        'dorm': 'Dormitories'
    }
    return names.get(category, category.title())


# Default categories for the admin panel
DEFAULT_CATEGORIES = ['building', 'administration', 'library', 'lab', 'cafe', 'dorm', 'lecture_hall']