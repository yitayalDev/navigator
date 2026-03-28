"""
Telegram Bot Callback Handlers
Contains async handlers for inline keyboard callbacks and message handling
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from datetime import datetime

# Import from services and utils
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.database import db
from utils.config import CampusData
from bot.handlers import get_category_emoji, get_category_display_name


# Global pending shares dictionary (will be set from main app)
pending_shares = {}


def set_pending_shares(shares_dict):
    """Set the pending shares dictionary from the main app"""
    global pending_shares
    pending_shares = shares_dict


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
                            callback_data=f"location_{loc['name']}"
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
            [InlineKeyboardButton("🏰 Fasil Campus", callback_data='campus_fasil')],
        ]
        
        await query.edit_message_text(
            text="🏛️ *Select a Campus:*",
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
            text="⏳ *Waiting for location...*\n\n"
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
            except Exception as e:
                await query.edit_message_text(
                    text=f"❌ Error sending location: {str(e)}",
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
            text="❌ *Share Location Cancelled*\n\n"
                "Your location was not sent to anyone.",
            parse_mode='Markdown'
        )
        return


async def handle_location_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location messages sent by users"""
    user = update.effective_user
    location = update.message.location
    
    # Store the location in the database
    db.update_user_location(user.id, f"{location.latitude},{location.longitude}")
    
    await update.message.reply_text(
        f"📍 Location received!\n\n"
        f"Latitude: {location.latitude}\n"
        f"Longitude: {location.longitude}\n\n"
        f"You can now share this location with friends using /menu"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    # Check if user wants to share location
    text = update.message.text.lower()
    
    if text in ['share', 'share my location', 'share location']:
        keyboard = [
            [
                InlineKeyboardButton("📤 Share Current Location", callback_data='share_location_start'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📤 *Share Your Location*\n\nClick the button below to share your current location with friends:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        # Default response with help
        await update.message.reply_text(
            "👋 Hello! I'm the UOG Student Navigation Bot.\n\n"
            "Use /menu to see available options or /help for commands."
        )


def get_pending_shares():
    """Get the pending shares dictionary for external access"""
    return pending_shares