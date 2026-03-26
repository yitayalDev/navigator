"""
UOG Student Navigation Telegram Bot
University of Gondar Campus Navigation Bot

This bot helps students and visitors navigate the University of Gondar campuses:
- Maraki Campus (Main Campus)
- Tewodros Campus
- Fasil Campus

Features:
- List all locations
- Filter by campus
- Filter by category (buildings, cafes, libraries, lecture halls)
- Get directions to locations
- Find nearest locations
"""
import os
import sys
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes, 
    MessageHandler, 
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from config import config, CampusData
from routing_service import routing_service

# Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_CAMPUS, SELECTING_CATEGORY, SELECTING_LOCATION = range(3)

# User registry to store users who have started the bot
# Format: {username: {'chat_id': chat_id, 'name': name, 'username': username}}
user_registry = {}

# Store pending share requests (mirrors server.py's pending_shares)
# Format: {user_id: {'state': ..., 'friend_username': ..., 'sender_name': ..., 'timestamp': ...}}
pending_shares = {}


def register_user(update: Update):
    """Register a user who started the bot."""
    user = update.effective_user
    if user:
        username = user.username.lower() if user.username else None
        if username:
            user_registry[username] = {
                'chat_id': update.effective_chat.id,
                'name': user.first_name,
                'username': username
            }
        # Also register by user_id for direct sharing
        user_registry[str(user.id)] = {
            'chat_id': update.effective_chat.id,
            'name': user.first_name,
            'username': username,
            'user_id': user.id
        }


def get_user_chat_id(identifier):
    """Get chat_id for a user by username or user_id."""
    identifier = identifier.lower() if isinstance(identifier, str) else str(identifier)
    user_data = user_registry.get(identifier)
    if user_data:
        return user_data.get('chat_id')
    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show campus selection first."""
    # Register the user
    register_user(update)
    
    # Check if there are arguments (like coordinates from the app)
    args = context.args
    
    # Create inline keyboard for campus selection
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
            InlineKeyboardButton("🏥 Fasil Campus", callback_data='campus_fasil'),
        ],
    ]
    
    # If coordinates were passed from the app, also add option to share specific location
    if args:
        coords_arg = args[0]
        try:
            # Parse coordinates
            if ',' in coords_arg:
                lat, lng = coords_arg.split(',')
                lat = float(lat.strip())
                lng = float(lng.strip())
                coords = f"{lat},{lng}"
                
                # Add share specific location button
                keyboard.insert(0, [
                    InlineKeyboardButton("📍 Share This Location", callback_data=f'share_current_{coords}'),
                ])
        except:
            pass
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
🏛️ *Welcome to UOG Student Navigation Bot!*

I can help you navigate the University of Gondar campuses.

*What would you like to do?*
• 📤 Share your current location with friends
• 🏫 Explore campus locations and buildings
• 🗺️ Get directions to campus locations
"""
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_message = """
📚 *Available Commands:*

/start - Start the bot and show welcome message
/menu - Show main menu
/campuses - List all campuses
/locations - Show all locations
/buildings - Show only buildings
/cafes - Show only cafes
/libraries - Show only libraries
/lecture - Show lecture halls
/nearby - Find nearby locations

📤 *Location Sharing:*
• Tap any location → "Share to Friend" button
• Or use: /share [username] [lat,lng]
• Example: /share john_doe 12.5980,37.3900

📱 *Mobile App:*
Use the UOG Navigator app to:
• Get turn-by-turn directions
• Share your live location
• View interactive campus maps

🔹 *Campus Codes:*
• maraki - Main Campus
• tewodros - Tewodros Campus
• fasil - Fasil Campus

📍 Use /campus [code] to see locations in a specific campus!
    """
    await update.message.reply_text(
        help_message,
        parse_mode='Markdown'
    )


def get_main_menu_keyboard():
    """Create main menu keyboard."""
    keyboard = [
        ['📍 All Locations', '🏫 Campuses'],
        ['🏢 Buildings', '☕ Cafes'],
        ['📚 Libraries', '🎓 Lecture Halls'],
        ['📱 Mobile App', '❓ Help']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def campuses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all campuses."""
    message = "🏛️ *University of Gondar Campuses:*\n\n"
    
    for campus_id, campus_info in CampusData.CAMPUSES.items():
        locations_count = len(CampusData.get_locations_by_campus(campus_id))
        message += f"*{campus_info['name']}*\n"
        message += f"📝 {campus_info['description']}\n"
        message += f"📍 {locations_count} locations\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def locations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all locations."""
    message = "📍 *All University Locations:*\n\n"
    
    for i, loc in enumerate(CampusData.LOCATIONS, 1):
        emoji = get_category_emoji(loc['category'])
        message += f"{emoji} *{loc['name']}*\n"
        message += f"   📌 {loc['campus'].title()} Campus\n"
        message += f"   📝 {loc['description']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def buildings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show only buildings."""
    buildings = CampusData.get_locations_by_category('building')
    message = "🏢 *Buildings:*\n\n"
    
    for loc in buildings:
        message += f"• *{loc['name']}* - {loc['campus'].title()} Campus\n"
        message += f"  📝 {loc['description']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def cafes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show only cafes."""
    cafes = CampusData.get_locations_by_category('cafe')
    message = "☕ *Cafés & Food:*\n\n"
    
    for loc in cafes:
        message += f"• *{loc['name']}* - {loc['campus'].title()} Campus\n"
        message += f"  📝 {loc['description']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def libraries_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show only libraries."""
    libraries = CampusData.get_locations_by_category('library')
    message = "📚 *Libraries:*\n\n"
    
    for loc in libraries:
        message += f"• *{loc['name']}* - {loc['campus'].title()} Campus\n"
        message += f"  📝 {loc['description']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def lecture_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show lecture halls."""
    lectures = CampusData.get_locations_by_category('lecture_hall')
    message = "🎓 *Lecture Halls:*\n\n"
    
    for loc in lectures:
        message += f"• *{loc['name']}* - {loc['campus'].title()} Campus\n"
        message += f"  📝 {loc['description']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu."""
    await update.message.reply_text(
        "📱 *Main Menu* - Select an option:",
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard()
    )


async def app_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mobile app information."""
    message = """
📱 *UOG Student Navigation Mobile App*

Download our mobile app for the full navigation experience:
• 🗺️ Interactive campus maps
• 🚶 Turn-by-turn directions
• 📍 Real-time location tracking
• 🔍 Search and filter locations
• 📡 Bluetooth crowd detection
• 📤 Share location with friends

 The app is available for:
• Android
• iOS
• Windows
• And more...

Coming soon on app stores!
    """
    await update.message.reply_text(message, parse_mode='Markdown')


async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Share location with a friend.
    
    Usage: /share [username] [lat,lng] or /share [username] [location name]
    Example: /share john_doe 12.5980,37.3900
    Example: /share john_doe Main Library
    
    Note: Your friend must have started the bot first for this to work!
    """
    # Register the sender
    register_user(update)
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📤 *Share Location with Friend*\n\n"
            "Usage: /share [username] [lat,lng]\n"
            "Or: /share [username] [location name]\n\n"
            "Examples:\n"
            "• /share john_doe 12.5980,37.3900\n"
            "• /share john_doe Main Library\n\n"
            "⚠️ Your friend must have started the bot first!\n\n"
            "The friend will receive a message with the location and a Google Maps link.",
            parse_mode='Markdown'
        )
        return
    
    # Parse the arguments
    # Last argument is the location (coords or name), first is username
    username = context.args[0].strip().lower()
    location_arg = ' '.join(context.args[1:]).strip()
    
    coords = None
    location_name = None
    
    # Check if it's coordinates (contains comma)
    if ',' in location_arg:
        try:
            lat, lng = location_arg.split(',')
            lat = float(lat.strip())
            lng = float(lng.strip())
            coords = f"{lat},{lng}"
            location_name = "Shared Location"
        except:
            await update.message.reply_text(
                "❌ Invalid coordinates format. Use: lat,lng\n"
                "Example: 12.5980,37.3900"
            )
            return
    else:
        # Search for location by name
        location_arg_lower = location_arg.lower()
        for loc in CampusData.LOCATIONS:
            if location_arg_lower in loc['name'].lower():
                coords = loc['coords']
                location_name = loc['name']
                break
        
        if not coords:
            await update.message.reply_text(
                f"❌ Location '{location_arg}' not found.\n\n"
                f"Use coordinates instead: /share {username} 12.5980,37.3900\n"
                f"Or use /locations to see all available locations.",
                parse_mode='Markdown'
            )
            return
    
    # Send the location to friend
    await send_location_to_friend(update, context, username, coords, location_name)


async def sharelocation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Share current GPS location from Telegram with a friend.
    
    Usage: /sharelocation [lat,lng]
    Example: /sharelocation 12.5980,37.3900
    
    The bot will ask for the friend's username after receiving the location.
    OR use the menu button to share directly from Telegram.
    """
    # Register the sender
    register_user(update)
    
    if not context.args:
        await update.message.reply_text(
            "📍 *Share My Current Location*\n\n"
            "To share your current location with a friend:\n\n"
            "1. Open the UOG Navigator app\n"
            "2. Go to any location\n"
            "3. Tap the Telegram bot button\n"
            "4. Enter your friend's username\n\n"
            "The app will send your current GPS location to your friend!",
            parse_mode='Markdown'
        )
        return
    
    # Parse the coordinates
    coords_arg = context.args[0].strip()
    
    try:
        lat, lng = coords_arg.split(',')
        lat = float(lat.strip())
        lng = float(lng.strip())
        coords = f"{lat},{lng}"
    except:
        await update.message.reply_text(
            "❌ Invalid coordinates. Please try again from the app."
        )
        return
    
    # Ask for friend's username
    await update.message.reply_text(
        "📤 *Enter Your Friend's Username*\n\n"
        f"📍 Your current location: {coords}\n\n"
        "Please reply with your friend's Telegram username (without @)\n"
        "Example: john_doe\n\n"
        "⚠️ Your friend must have started the bot first!",
        parse_mode='Markdown'
    )
    
    # Store the location in context for the next message
    context.user_data['pending_current_location'] = {'coords': coords}


async def send_location_to_friend(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str, coords: str, location_name: str):
    """Send a location to a friend."""
    # Create the share message
    sender_name = update.message.from_user.first_name
    sender_username = update.message.from_user.username
    if sender_username:
        sender_name = f"@{sender_username}"
    
    maps_url = f"https://www.google.com/maps?q={coords}"
    
    share_message = f"""
📍 *Location Shared by Friend*

👤 *From:* {sender_name}

📍 *Location:* {location_name}
📌 *Coordinates:* {coords}

🗺️ [View on Google Maps]({maps_url})

_Sent via UOG Navigator Bot_
"""
    
    # Get friend's chat_id from registry
    friend_chat_id = get_user_chat_id(username)
    
    if friend_chat_id:
        # Send the location to the friend
        try:
            await context.bot.send_message(
                chat_id=friend_chat_id,
                text=share_message,
                parse_mode='Markdown'
            )
            
            # Send confirmation to sender
            await update.message.reply_text(
                f"✅ Location sent to @{username}!\n\n"
                f"📍 They received:\n"
                f"   {location_name}\n"
                f"   📌 {coords}\n"
                f"   🗺️ {maps_url}",
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Could not send to @{username}. Error: {str(e)}",
                parse_mode='Markdown'
            )
    else:
        # Friend not found - show instructions
        await update.message.reply_text(
            f"❌ @{username} has not started the bot yet!\n\n"
            f"Tell your friend to start the UOG Navigator Bot first by sending /start",
            parse_mode='Markdown'
        )
        
        # Also show the message that would be sent
        await update.message.reply_text(
            f"📤 *Message that would be sent to @{username}:*\n\n{share_message}",
            parse_mode='Markdown'
        )


async def mylocation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the user's current location and share it.
    
    Usage: /mylocation - Get your current location
    """
    await update.message.reply_text(
        "📍 *Share Your Current Location*\n\n"
        "To share your current location with friends:\n\n"
        "1. Open the UOG Navigator mobile app\n"
        "2. Go to any location\n"
        "3. Tap 'Share Location' button\n"
        "4. Choose Telegram or Bot to share\n\n"
        "Your current GPS coordinates will be shared with your friends!\n\n"
        "You can also share campus locations:\n"
        "• Browse a campus and tap on any location\n"
        "• Click 'Share to Friend' button\n"
        "• Enter your friend's username\n\n"
        "Try: /share [friend] Main Library",
        parse_mode='Markdown'
    )


async def directions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get directions to a location."""
    # Extract location name from command args
    if context.args:
        location_name = ' '.join(context.args).lower()
        for loc in CampusData.LOCATIONS:
            if location_name in loc['name'].lower():
                await send_directions(update, context, loc)
                return
        
        await update.message.reply_text(
            f"❓ Location '{location_name}' not found. Use /locations to see all locations."
        )
    else:
        await update.message.reply_text(
            "📍 Usage: /directions [location name]\n\n"
            "Example: /directions library\n"
            "\nTo get directions from your location:\n"
            "Usage: /from [lat,lng] [location name]\n"
            "Example: /from 12.5980,37.3900 library\n"
            "Use /locations to see all available locations."
        )


async def from_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get shortest path directions from a specific location to a destination.
    
    Usage: /from [origin_lat,origin_lng] [destination_name]
    Example: /from 12.5980,37.3900 library
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📍 Usage: /from [origin_lat,origin_lng] [destination_name]\n\n"
            "Example: /from 12.5980,37.3900 library\n\n"
            "This uses the SDMR server to calculate the shortest path!\n"
            "Use /locations to see all available locations."
        )
        return
    
    # Parse origin coordinates from first argument
    origin_arg = context.args[0]
    
    # Check if first argument contains comma (coordinates)
    if ',' in origin_arg:
        origin_coords = origin_arg
        destination_name = ' '.join(context.args[1:]).lower()
    else:
        # Maybe user forgot to include coordinates, treat entire arg as location name
        await update.message.reply_text(
            "❓ Please provide your coordinates in format: /from [lat,lng] [destination]\n\n"
            "Example: /from 12.5980,37.3900 library"
        )
        return
    
    # Validate coordinates format
    try:
        lat, lng = origin_coords.split(',')
        float(lat.strip())
        float(lng.strip())
    except:
        await update.message.reply_text(
            "❌ Invalid coordinates format. Use: lat,lng\n"
            "Example: 12.5980,37.3900"
        )
        return
    
    # Find the destination location
    for loc in CampusData.LOCATIONS:
        if destination_name in loc['name'].lower():
            await update.message.reply_text(
                "🧭 Calculating shortest path via SDMR server..."
            )
            await send_directions(update, context, loc, origin_coords)
            return
    
    await update.message.reply_text(
        f"❓ Location '{destination_name}' not found. Use /locations to see all locations."
    )


async def send_directions(update: Update, context: ContextTypes.DEFAULT_TYPE, location: dict, origin_coords: str = None):
    """Send directions to a specific location with shortest path using OSRM SDMR server."""
    # Handle both Update and CallbackQuery types
    if hasattr(update, 'callback_query'):
        # This is from a callback query
        query = update.callback_query
        message = await query.message.reply_text
    maps_url = f"https://www.google.com/maps/search/?api=1&query={location['coords']}"
    
    message = f"""
🗺️ *Directions to {location['name']}*

📍 *Location:* {location['name']}
🏛️ *Campus:* {location['campus'].title()}
📝 *Description:* {location['description']}
📌 *Coordinates:* {location['coords']}
"""
    
    # If origin coordinates provided, get shortest path from OSRM SDMR server
    if origin_coords:
        print(f"[BOT] Getting shortest path from {origin_coords} to {location['coords']}")
        route = routing_service.get_shortest_path(origin_coords, location['coords'])
        
        if route:
            distance_km = route['distance'] / 1000
            duration_min = route['duration'] / 60
            
            # Check if this is a fallback (direct distance) or actual OSRM route
            is_fallback = route.get('is_fallback', False)
            
            if is_fallback:
                message += f"""
⚠️ *Note: Using estimated path (road data not available in OSRM)*
   📏 Distance: ~{distance_km:.2f} km (straight line)
   ⏱️ Estimated walking time: ~{duration_min:.1f} minutes
"""
            else:
                message += f"""
🧭 *SHORTEST PATH (via OSRM):*
   📏 Distance: {distance_km:.2f} km
   ⏱️ Estimated time: {duration_min:.1f} minutes (walking)
   🚶 Mode: Pedestrian
"""
                
                # Add turn-by-turn directions
                directions = routing_service.get_directions(origin_coords, location['coords'])
                if directions:
                    message += f"\n{directions}"
        else:
            message += "\n⚠️ Could not calculate route from OSMR server.\n"
            # Try direct distance as fallback
            direct_distance = routing_service.calculate_distance(origin_coords, location['coords'])
            if direct_distance:
                message += f"📏 Direct distance: {direct_distance:.0f} meters\n"
    
    message += f"\n[📍 View on Google Maps]({maps_url})"
    
    # Create inline keyboard with share option
    keyboard = [
        [
            InlineKeyboardButton("📤 Share to Friend", callback_data=f'share_loc_{location["coords"]}_{location["name"]}'),
        ],
        [
            InlineKeyboardButton("🔙 Back to Locations", callback_data=f'category_{location["campus"]}_{location["category"]}'),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )


async def handle_location_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location messages sent by users."""
    # Check if user is in share location flow
    pending_mode = context.user_data.get('pending_share_mode')
    
    if pending_mode == 'waiting_location':
        # Get the location from the message
        location = update.message.location
        lat = location.latitude
        lng = location.longitude
        coords = f"{lat},{lng}"
        
        # Clear the pending mode
        del context.user_data['pending_share_mode']
        
        # Ask for friend's username
        await update.message.reply_text(
            f"📍 *Location Received!*\n\n"
            f"Your location: {coords}\n\n"
            f"Now please reply with your friend's Telegram username (without @)\n"
            f"Example: john_doe\n\n"
            f"⚠️ Your friend must have started the bot first!",
            parse_mode='Markdown'
        )
        
        # Store location for next message
        context.user_data['pending_current_location'] = {'coords': coords}
        return
    
    # If not in share mode, just acknowledge
    await update.message.reply_text(
        "📍 Thank you for sharing your location!\n\n"
        "Use /menu to see available options."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    text = update.message.text
    
    # Check if user has a pending current location to share
    pending_location = context.user_data.get('pending_current_location')
    if pending_location:
        # User is sharing their current location to a friend
        friend_username = text.strip().lower()
        coords = pending_location['coords']
        
        # Clear the pending location
        del context.user_data['pending_current_location']
        
        # Send the location to friend
        await send_location_to_friend(update, context, friend_username, coords, "Current Location")
        return
    
    # Check if user has a pending share location
    pending_share = context.user_data.get('pending_share_location')
    if pending_share:
        # User is sharing a location to a friend
        friend_username = text.strip().lower()
        coords = pending_share['coords']
        name = pending_share['name']
        
        # Clear the pending share
        del context.user_data['pending_share_location']
        
        # Send the location to friend
        await send_location_to_friend(update, context, friend_username, coords, name)
        return
    
    # Check if user is waiting to enter friend's username (from share_location_start button)
    pending_mode = context.user_data.get('pending_share_mode')
    if pending_mode == 'waiting_friend_username':
        # User entered friend's username - now get location from app
        friend_username = text.strip()
        if friend_username.startswith('@'):
            friend_username = friend_username[1:]
        friend_username = friend_username.lower()
        
        sender_name = context.user_data.get('sender_name', 'A friend')
        
        # Check if friend exists in database
        friend = db.get_user(username=friend_username)
        
        if not friend:
            await update.message.reply_text(
                f"User @{friend_username} not found!\n\n"
                f"Please make sure your friend has started the bot first."
            )
            return
        
        # Try to get location from app via API
        coords = None
        user_id = update.effective_user.id
        try:
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
        except Exception as e:
            logger.info(f"Could not get location from app: {e}")
        
        # Clear the pending mode from context
        if 'pending_share_mode' in context.user_data:
            del context.user_data['pending_share_mode']
        
        # Also clear from pending_shares
        if user_id in pending_shares:
            del pending_shares[user_id]
        
        if coords:
            # Got location from app, send directly to friend
            lat, lng = coords.split(',') if coords else ('0', '0')
            maps_link = f"https://www.google.com/maps?q={lat},{lng}"
            
            # Send location to friend
            try:
                chat_id = friend.get('chat_id')
                if chat_id:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"📍 *Location from @{sender_name}*\n\n"
                            f"📌 *Coordinates:* {lat},{lng}\n"
                            f"🔗 *Map Link:* {maps_link}",
                        parse_mode='Markdown'
                    )
                    
                    # Confirm to sender
                    await update.message.reply_text(
                        text=f"✅ Location sent to @{friend_username}!\n\n"
                            f"📌 Coordinates: {lat},{lng}\n"
                            f"🔗 Map: {maps_link}"
                    )
                else:
                    await update.message.reply_text(
                        text=f"Could not send to @{friend_username}. They may not have started the bot yet."
                    )
            except Exception as e:
                await update.message.reply_text(
                    text=f"Error sending location: {str(e)}"
                )
        else:
            # Can't get location immediately, set state and tell user to open app
            # Store pending share request
            pending_shares[user_id] = {
                'state': 'waiting_location_from_app',
                'friend_username': friend_username,
                'sender_name': sender_name,
                'timestamp': datetime.now(),
                'coords': ''
            }
            
            await update.message.reply_text(
                text=f"✅ Friend Found: @{friend_username}\n\n"
                    "📱 Please open the UOG Navigator app and share your location.\n\n"
                    "I'll automatically get your current GPS location from the app and send it to your friend!",
                parse_mode='Markdown'
            )
        return
    
    if pending_mode == 'waiting_username_with_location':
        # We already have location from app, just need friend's username
        friend_username = text.strip()
        if friend_username.startswith('@'):
            friend_username = friend_username[1:]
        friend_username = friend_username.lower()
        
        # Get the coordinates from context
        coords = context.user_data.get('coords', '')
        sender_name = context.user_data.get('sender_name', 'A friend')
        
        # Clear the pending mode
        del context.user_data['pending_share_mode']
        if 'coords' in context.user_data:
            del context.user_data['coords']
        
        # Check if friend exists in database
        friend = db.get_user(username=friend_username)
        
        if not friend:
            await update.message.reply_text(
                f"User @{friend_username} not found!\n\n"
                f"Please make sure your friend has started the bot first."
            )
            return
        
        # Generate Google Maps link
        lat, lng = coords.split(',') if coords else (0, 0)
        maps_link = f"https://www.google.com/maps?q={lat},{lng}"
        
        # Send location directly to friend
        try:
            chat_id = friend.get('chat_id')
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Location from @{sender_name}\n\n"
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
        return
    
    if text == '📍 All Locations':
        await locations_command(update, context)
    elif text == '🏫 Campuses':
        await campuses_command(update, context)
    elif text == '🏢 Buildings':
        await buildings_command(update, context)
    elif text == '☕ Cafes':
        await cafes_command(update, context)
    elif text == '📚 Libraries':
        await libraries_command(update, context)
    elif text == '🎓 Lecture Halls':
        await lecture_command(update, context)
    elif text == '📱 Mobile App':
        await app_info_command(update, context)
    elif text == '❓ Help':
        await help_command(update, context)
    else:
        # Search for location
        text_lower = text.lower()
        for loc in CampusData.LOCATIONS:
            if text_lower in loc['name'].lower():
                await send_directions(update, context, loc)
                return
        
        await update.message.reply_text(
            "❓ I didn't understand that. Use /menu to see available options.",
            reply_markup=get_main_menu_keyboard()
        )


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


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    error_message = "❌ An error occurred. Please try again or use /help."
    
    if update and update.message:
        try:
            await update.message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    elif update and update.callback_query:
        try:
            await update.callback_query.message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    # Handle callback data
    callback_data = query.data
    
    if callback_data.startswith('campus_'):
        # Show categories in a campus (buildings, labs, libraries, etc.)
        campus_id = callback_data.replace('campus_', '')
        locations = CampusData.get_locations_by_campus(campus_id)
        campus_info = CampusData.CAMPUSES.get(campus_id, {})
        
        if locations:
            # Group locations by category
            categories = {}
            for loc in locations:
                category = loc['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append(loc)
            
            # Create keyboard with category buttons
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
            
            # Add back button
            keyboard.append([
                InlineKeyboardButton("🔙 Back to Campuses", callback_data='back_campuses')
            ])
            
            message = f"🏛️ *{campus_info.get('name', campus_id.title())} Campus*\n\n"
            message += f"📝 {campus_info.get('description', '')}\n\n"
            message += f"📊 Total locations: {len(locations)}\n\n"
            message += "*Select a category to view locations:*"
            
            await query.edit_message_text(
                text=message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif callback_data.startswith('category_'):
        # Show locations in a specific category within a campus
        parts = callback_data.split('_')
        if len(parts) >= 3:
            campus_id = parts[1]
            category = parts[2]
            
            locations = CampusData.get_locations_by_campus(campus_id)
            locations = [loc for loc in locations if loc['category'] == category]
            campus_info = CampusData.CAMPUSES.get(campus_id, {})
            category_display = get_category_display_name(category)
            emoji = get_category_emoji(category)
            
            if locations:
                # Create keyboard with locations in this category
                keyboard = []
                for loc in locations:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📍 {loc['name']}", 
                            callback_data=f'location_{loc["name"]}'
                        )
                    ])
                
                # Add back button to return to categories
                keyboard.append([
                    InlineKeyboardButton(f"🔙 Back to {category_display}", callback_data=f'campus_{campus_id}')
                ])
                
                message = f"{emoji} *{category_display} in {campus_info.get('name', campus_id.title())} Campus*\n\n"
                message += f"📊 {len(locations)} location(s)\n\n"
                message += "Select a location to get directions:"
                
                await query.edit_message_text(
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
    
    elif callback_data.startswith('location_'):
        # Get directions to selected location
        location_name = callback_data.replace('location_', '')
        
        for loc in CampusData.LOCATIONS:
            if location_name.lower() == loc['name'].lower():
                await query.edit_message_text(
                    text=f"📍 *Getting directions to {loc['name']}...*",
                    parse_mode='Markdown'
                )
                await send_directions(update, context, loc)
                return
        
        await query.edit_message_text(
            text=f"❓ Location '{location_name}' not found.",
            parse_mode='Markdown'
        )
    
    elif callback_data == 'back_campuses':
        # Show campus selection again
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
        ]
        
        await query.edit_message_text(
            text="🏛️ *Select a Campus:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif callback_data == 'back_menu':
        # Show main menu
        await query.edit_message_text(
            text="📱 *Main Menu* - Select an option:",
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
    
    elif callback_data.startswith('share_loc_'):
        # Handle share location to friend
        # Format: share_loc_coords_name
        parts = callback_data.split('_', 2)  # Split into max 2 parts to keep name together
        if len(parts) >= 3:
            coords = parts[1]
            name = '_'.join(parts[2:])  # Rejoin the rest as name
            
            # Ask user for friend's username
            await query.edit_message_text(
                text=f"📤 *Share {name} to Friend*\n\n"
                     f"📍 Location: {name}\n"
                     f"📌 Coordinates: {coords}\n\n"
                     f"Please reply with your friend's Telegram username (without @)\n"
                     f"Example: john_doe\n\n"
                     f"Or use /share {name.replace(' ', '_')} {coords} [username] command\n"
                     f"Example: /share {name.replace(' ', '_')} {coords} john_doe",
                parse_mode='Markdown'
            )
            
            # Store the location info in context for the next message
            context.user_data['pending_share_location'] = {'coords': coords, 'name': name}
    
    elif callback_data == 'share_my_location':
        # Handle share my current location to friend - ask user to share location in Telegram
        await query.edit_message_text(
            text="📤 *Share Your Current Location*\n\n"
                "To share your current location with a friend:\n\n"
                "1. 📍 *Click the attachment button (paper clip) in this chat*\n"
                "2. Select \"Location\" from the menu\n"
                "3. Send your current location\n\n"
                "I will then ask for your friend's username to send the location to.\n\n"
                "⚠️ Your friend must have started the bot first!",
            parse_mode='Markdown'
        )
        
        # Set pending mode to wait for location
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        context.user_data['pending_share_mode'] = 'waiting_location'
        context.user_data['sender_name'] = username
    
    elif callback_data == 'share_location_start':
        # Start share location flow - ask for friend's username
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Ask for friend's username
        await query.edit_message_text(
            text="Share Your Current Location\n\n"
                "Please enter your friend's Telegram username (without @)\n"
                "Example: john_doe\n\n"
                "Then send your location from Telegram."
        )
        
        # Store user as waiting for friend's username
        context.user_data['pending_share_mode'] = 'waiting_friend_username'
        context.user_data['sender_name'] = username
        
        # Also store in pending_shares for API access
        pending_shares[user_id] = {
            'state': 'waiting_friend_username',
            'sender_name': username,
            'timestamp': datetime.now()
        }
    
    elif callback_data.startswith('confirm_send_'):
        # Handle confirm send button click
        # Format: confirm_send_friend_username_coords
        parts = callback_data.replace('confirm_send_', '').split('_')
        if len(parts) >= 2:
            friend_username = parts[0]
            coords = '_'.join(parts[1:])
            
            sender_id = update.effective_user.id
            sender_name = update.effective_user.username or update.effective_user.first_name
            
            # Send location to friend using the same function
            from database import MongoDB
            db = MongoDB()
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
                        text=f"📍 *Location Shared by Friend*\n\n"
                            f"📱 *From:* @{sender_name}\n"
                            f"📌 *Coordinates:* {coords}\n"
                            f"🔗 *Map Link:* {maps_link}",
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
            
            # Clean up
            if 'pending_share_mode' in context.user_data:
                del context.user_data['pending_share_mode']
            return
    
    elif callback_data == 'cancel_send':
        # Handle cancel button click
        if 'pending_share_mode' in context.user_data:
            del context.user_data['pending_share_mode']
        if 'pending_share_location' in context.user_data:
            del context.user_data['pending_share_location']
        if 'pending_current_location' in context.user_data:
            del context.user_data['pending_current_location']
        
        await query.edit_message_text(
            text="❌ *Share Location Cancelled*\n\n"
                "Your location was not sent to anyone.",
            parse_mode='Markdown'
        )
        return
    
    elif callback_data.startswith('share_current_'):
        # Handle sharing current location from app with coordinates
        coords = callback_data.replace('share_current_', '')
        
        # Ask for friend's username
        await query.edit_message_text(
            text="📤 *Share My Current Location*\n\n"
                 f"📍 Your current location: {coords}\n\n"
                 "Please reply with your friend's Telegram username (without @)\n"
                 "Example: john_doe\n\n"
                 "⚠️ Your friend must have started the bot first!",
            parse_mode='Markdown'
        )
        
        # Store the location in context for the next message
        context.user_data['pending_current_location'] = {'coords': coords}


def main():
    """Main function to run the bot."""
    # Validate configuration
    if not config.validate():
        print("\n" + "="*50)
        print("ERROR: Bot configuration is incomplete!")
        print("="*50)
        print("\nPlease configure your Telegram Bot Token:")
        print("1. Edit the .env file in the backend folder")
        print("2. Set TELEGRAM_BOT_TOKEN=your_token_here")
        print("3. Or set the environment variable UOG_NAVIGATOR_TELEGRAM_TOKEN")
        print("\nGet your bot token from @BotFather on Telegram")
        print("="*50 + "\n")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("Starting UOG Student Navigation Bot...")
    print("="*50)
    
    # Get bot token from secure config
    bot_token = config.get_bot_token()
    print(f"Bot token loaded securely")
    print(f"Loaded {len(CampusData.LOCATIONS)} locations")
    print(f"Loaded {len(CampusData.CAMPUSES)} campuses")
    print("="*50 + "\n")
    
    # Build application
    app = ApplicationBuilder().token(bot_token).build()
    
    # Add command handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('menu', menu_command))
    app.add_handler(CommandHandler('campuses', campuses_command))
    app.add_handler(CommandHandler('locations', locations_command))
    app.add_handler(CommandHandler('buildings', buildings_command))
    app.add_handler(CommandHandler('cafes', cafes_command))
    app.add_handler(CommandHandler('libraries', libraries_command))
    app.add_handler(CommandHandler('lecture', lecture_command))
    app.add_handler(CommandHandler('directions', directions_command))
    app.add_handler(CommandHandler('from', from_command))
    app.add_handler(CommandHandler('app', app_info_command))
    app.add_handler(CommandHandler('share', share_command))
    app.add_handler(CommandHandler('sharelocation', sharelocation_command))
    app.add_handler(CommandHandler('mylocation', mylocation_command))
    
    # Add callback query handler for inline buttons
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Add message handler for text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add message handler for location messages
    app.add_handler(MessageHandler(filters.LOCATION, handle_location_message))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    print("Bot handlers registered")
    print("Bot is now running!")
    print("\nPress Ctrl-C to stop the bot.\n")
    
    # Start polling
    app.run_polling()


if __name__ == '__main__':
    main()
